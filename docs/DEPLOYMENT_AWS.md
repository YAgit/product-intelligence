# AWS Deployment Runbook

## Purpose

This runbook describes the production-oriented AWS deployment target for the Product Intelligence Platform:

- Next.js frontend on AWS Amplify Hosting.
- Unchanged FastAPI Docker image in Amazon Elastic Container Registry (ECR).
- FastAPI service on Amazon ECS Express Mode using AWS Fargate.

This is an operational document, not infrastructure implementation. Do not add AWS SDK calls, Amplify libraries, deployment manifests, CloudFormation, CDK, or Terraform to the application package merely to deploy it. If infrastructure as code is later required, maintain it as an independently owned infrastructure package.

## Provider-Neutrality Rules

- Build the backend from the repository's existing `Dockerfile` without altering application logic.
- Keep `NEXT_PUBLIC_API_BASE_URL` as the frontend's only backend-location setting.
- Keep `FRONTEND_ORIGIN`, `OPENFDA_API_KEY`, and `OPENROUTER_API_KEY` in the backend runtime.
- Store production secrets in AWS Secrets Manager and reference them from the ECS task definition.
- Keep Amplify build settings in the Amplify console unless a separate infrastructure package owns them.
- Do not expose backend secrets to Amplify or any `NEXT_PUBLIC_*` variable.
- Use ECS Express Mode before adding manually managed load balancers, networking, autoscaling, or orchestration.

## Target Architecture

```text
Browser
  -> AWS Amplify Hosting: Next.js frontend
  -> HTTPS
  -> ECS Express Mode endpoint
       -> Application Load Balancer managed by Express Mode
       -> ECS service on Fargate
       -> FastAPI container from ECR
            -> openFDA
            -> OpenRouter

Secrets Manager -> ECS task environment
CloudWatch Logs <- ECS task logs
```

Express Mode supplies the public HTTPS endpoint, load balancing, Fargate service, autoscaling defaults, and deployment monitoring. Customize those resources only when a concrete requirement cannot be met by Express Mode.

## Prerequisites

- An AWS account and a selected Region.
- AWS CLI authenticated to the target account and Region.
- Permissions for Amplify Hosting, ECR, ECS, Fargate, IAM, Secrets Manager, and CloudWatch Logs.
- Docker with support for the target Fargate architecture; use `linux/amd64` unless the task definition deliberately selects ARM64.
- A default VPC with public subnets, or explicitly selected subnets suitable for an internet-facing Express Mode service.
- Repository access for Amplify Hosting.
- `OPENROUTER_API_KEY`; `OPENFDA_API_KEY` is optional but recommended.
- Agreed environment name, AWS Region, resource names, and cost owner.

Before creating resources, record these values in the independently managed deployment inventory:

```text
AWS account ID
AWS Region
Environment name
ECR repository name
ECS service name
Amplify application and branch
Frontend origin/custom domain
Backend origin/custom domain
Secret ARNs
Application revision/image digest
```

## 1. Verify the Application Artifact

Run the application checks before publishing an image:

```bash
.venv/bin/pytest
cd frontend
npm ci
npm test
npm run lint
npm run typecheck
npm run build
```

From the repository root, build the same backend image that will be pushed to ECR:

```bash
docker build --platform linux/amd64 -t fdasearch-backend:verify .
```

Run it locally with secrets supplied by the operator's approved secret mechanism, then confirm `/api/v1/health`, drug search, device search, summaries, and chat. Do not put literal secret values in commands, build arguments, image layers, or logs.

## 2. Create the ECR Repository

Choose immutable release tags, normally the full source revision. Do not deploy `latest` as the only release identifier.

```bash
AWS_REGION="us-east-1"
ECR_REPOSITORY="fdasearch-backend"

aws ecr create-repository \
  --region "$AWS_REGION" \
  --repository-name "$ECR_REPOSITORY" \
  --image-scanning-configuration scanOnPush=true \
  --image-tag-mutability IMMUTABLE
```

If the repository already exists, inspect and reuse it rather than recreating it. Configure a lifecycle policy only when retention requirements are agreed; do not delete historical release images casually.

Authenticate Docker, build, tag, and push:

```bash
AWS_ACCOUNT_ID="123456789012"
AWS_REGION="us-east-1"
ECR_REPOSITORY="fdasearch-backend"
RELEASE_TAG="full-source-revision"
ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY"

aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

docker build --platform linux/amd64 -t "$ECR_URI:$RELEASE_TAG" .
docker push "$ECR_URI:$RELEASE_TAG"
aws ecr describe-images \
  --region "$AWS_REGION" \
  --repository-name "$ECR_REPOSITORY" \
  --image-ids imageTag="$RELEASE_TAG"
```

Record the returned image digest. Production releases should be traceable to both a source revision and an ECR digest.

## 3. Store Backend Secrets

Create separate Secrets Manager secrets for the backend credentials, or use an approved existing secret hierarchy:

- `fdasearch/<environment>/openrouter-api-key`
- `fdasearch/<environment>/openfda-api-key`

Enter secret values through the AWS console or an approved secret-input mechanism that does not expose them in shell history. Record only the secret ARNs in the deployment inventory.

Grant the ECS task execution role permission to retrieve only these secret ARNs and to use their KMS key when a customer-managed key is used. Do not grant wildcard Secrets Manager access.

## 4. Create ECS Express Mode Roles

ECS Express Mode requires:

- A task execution role trusted by `ecs-tasks.amazonaws.com`, with `AmazonECSTaskExecutionRolePolicy` and narrowly scoped access to the selected secrets.
- An infrastructure role trusted by `ecs.amazonaws.com`, with `AmazonECSInfrastructureRoleforExpressGatewayServices`.

Follow the current AWS Express Mode IAM instructions rather than copying account-specific policies into this repository. Keep the application task role separate; the current application does not require AWS API access and therefore should not receive permissions by default.

## 5. Define the Fargate Task

Use a custom task definition with Express Mode because it permits explicit Secrets Manager references and logging configuration. Store the task-definition JSON in an external deployment workspace or infrastructure package, not the application package.

The task definition must include:

- `family`: environment-specific family such as `fdasearch-api-demo`.
- `networkMode`: `awsvpc`.
- `requiresCompatibilities`: `FARGATE`.
- Appropriate task CPU and memory; begin with the smallest values validated by representative searches and AI calls.
- The task execution role ARN.
- One primary container named exactly `Main`.
- ECR image pinned to the release tag or digest.
- One named TCP port mapping for container port `8000`.
- Non-secret environment variable `FRONTEND_ORIGIN` set to the exact Amplify HTTPS origin.
- Secrets `OPENROUTER_API_KEY` and, when used, `OPENFDA_API_KEY`, referenced by Secrets Manager ARN.
- The `awslogs` log driver targeting an environment-specific CloudWatch Logs group.
- A read-only root filesystem only after compatibility has been verified; do not introduce it speculatively.

Create the CloudWatch log group before registering the task definition and set an agreed retention period. Register the task definition with `aws ecs register-task-definition`, then record the returned revision ARN.

Express Mode custom task definitions require the primary container name `Main`, a single named TCP port mapping, and Fargate compatibility.

## 6. Create the ECS Express Mode Service

Create the service from the registered task definition:

```bash
AWS_REGION="us-east-1"
INFRASTRUCTURE_ROLE_ARN="arn:aws:iam::123456789012:role/ecsInfrastructureRoleForExpressServices"
TASK_DEFINITION_ARN="arn:aws:ecs:us-east-1:123456789012:task-definition/fdasearch-api-demo:1"

aws ecs create-express-gateway-service \
  --region "$AWS_REGION" \
  --infrastructure-role-arn "$INFRASTRUCTURE_ROLE_ARN" \
  --task-definition-arn "$TASK_DEFINITION_ARN" \
  --health-check-path "/api/v1/health" \
  --monitor-resources
```

If the account has no default VPC or the default network is unsuitable, select the approved VPC and subnets through the current Express Mode console or CLI options. Do not build a full custom ECS platform unless Express Mode cannot satisfy a documented requirement.

Wait for the service status to become `ACTIVE`, then record its `https://<service-name>.ecs.<region>.on.aws` URL. Verify:

```bash
curl --fail --show-error "https://<service-name>.ecs.<region>.on.aws/api/v1/health"
```

The expected response is `{"status":"ok"}`.

## 7. Deploy Next.js with Amplify Hosting

The frontend lives in a subdirectory, so configure it as a monorepo application in the Amplify console:

1. Open Amplify Hosting and choose **Create new app**.
2. Connect the repository and select the release branch.
3. Select **My app is a monorepo**.
4. Set the application root to `frontend`. Amplify should set `AMPLIFY_MONOREPO_APP_ROOT=frontend`.
5. Confirm the install command is `npm ci`.
6. Confirm the build command is `npm run build` and the build output is `.next`.
7. Set `NEXT_PUBLIC_API_BASE_URL` to the ECS Express Mode HTTPS origin, without a trailing slash.
8. Do not place `OPENROUTER_API_KEY` or `OPENFDA_API_KEY` in Amplify.
9. Save and deploy.

If Amplify does not expose `NEXT_PUBLIC_API_BASE_URL` to the Next.js build automatically, configure the build settings in the Amplify console to write only that public variable into `frontend/.env.production` before `npm run build`. Keep those build settings in Amplify rather than committing `amplify.yml` during this phase.

After Amplify assigns the frontend URL, update the backend task definition so `FRONTEND_ORIGIN` exactly matches it, register a new task revision, and update the Express Mode service. Then retest browser CORS behavior. A planned custom frontend domain can avoid this two-step update.

## 8. Domains and TLS

- Amplify supplies an HTTPS `amplifyapp.com` domain and supports custom domains.
- ECS Express Mode supplies an HTTPS `ecs.<region>.on.aws` application URL.
- Add Route 53 and AWS-managed certificates only when a custom-domain requirement exists.
- When either public origin changes, update `NEXT_PUBLIC_API_BASE_URL` and `FRONTEND_ORIGIN`, redeploy the affected services, and repeat the verification checklist.

Do not add an API gateway, CloudFront distribution, WAF, or custom load balancer without a concrete requirement.

## 9. Verification Checklist

Verify from a clean browser session:

- ECS `/api/v1/health` returns HTTP 200.
- Amplify `/` loads drug search.
- Amplify `/devices` loads device search.
- Drug name and NDC searches work.
- Ambiguous drug matches require selection.
- Device DI, UDI text, brand, and model/catalog searches work.
- Product and device summaries work.
- Product and device chat work, including provider fallback messaging where safely testable.
- Browser requests have no CORS failures.
- External-service failures return useful application messages without stack traces.
- CloudWatch receives application logs without secrets or full external payloads.
- No API key appears in Amplify artifacts, page source, or browser requests.

## 10. Monitoring and Operations

- Use the ECS Express Mode service status and deployment monitor for service health.
- Use CloudWatch Logs for FastAPI application and container logs.
- Configure log retention deliberately to control cost.
- Review ECS task CPU, memory, restart count, response time, and 5xx behavior after representative use.
- Use Amplify build history and access logs available to the selected plan for frontend diagnosis.
- Configure alarms only for concrete operational requirements; avoid speculative monitoring infrastructure.

## 11. Release and Rollback

For each backend release:

1. Build and push an immutable ECR tag.
2. Record the image digest.
3. Register a new task-definition revision referencing that image.
4. Update the Express Mode service and monitor the deployment.
5. Run the verification checklist before declaring the release complete.

For each frontend release, deploy the matching source revision through Amplify and verify it against the intended backend API contract.

To roll back the backend, update Express Mode to the last verified task-definition revision or register a new revision pointing to the last verified image digest. To roll back the frontend, redeploy the last verified Amplify build. Roll back both when the API contract changed.

## 12. Teardown

Teardown is destructive and must be explicitly authorized. Resolve exact resource identifiers before deleting anything.

For an isolated environment, remove resources in this order:

1. Amplify custom-domain associations and app/branch.
2. ECS Express Mode service, monitoring until deletion completes.
3. Unused task-definition revisions according to the retention policy.
4. Environment-specific CloudWatch log groups when logs no longer need retention.
5. Environment-specific secrets after confirming they are not shared.
6. ECR images and repository only after confirming no environment depends on them.
7. Environment-specific IAM roles and policies after dependency checks.

Do not remove shared VPCs, subnets, domains, certificates, roles, secrets, or ECR repositories without separate confirmation.

## Official References

- [Deploy Next.js with Amplify Hosting](https://docs.aws.amazon.com/amplify/latest/userguide/getting-started-next.html)
- [Configure Amplify monorepo builds](https://docs.aws.amazon.com/amplify/latest/userguide/monorepo-configuration.html)
- [Push an image to ECR](https://docs.aws.amazon.com/AmazonECR/latest/userguide/docker-push-ecr-image.html)
- [Create an ECS Express Mode service](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-getting-started.html)
- [Use Secrets Manager secrets in ECS](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/specifying-sensitive-data-tutorial.html)
- [Send ECS logs to CloudWatch](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/using_awslogs.html)

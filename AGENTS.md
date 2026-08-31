# Pharmaceutical Product Search with AI Chat Web App

## Business Requirements

The next version of this project is adding a new feature to search pharmaceutical device details and function in a similar manner like the existing drug product search. the new version of the app shoild have - 
- Two separate search page, accessed by clicking a tab on eaither page. One of them is used for searching and proving key information and AI features for pharmaceutocal drugs based on NDC numbers or names. This is the existing feature in the current version. Another page that accepts device key fields listed below and provides key inforamtion and AI about the device. Key fields for devices to be accepted are::
UDI barcode text
Device Identifier
Brand name
Model or catalog number

Based on these entered fields  - the system should  normalize the input and query the appropriate endpoint.
The existing already works as follows:
- A search dialog where the user can enter a product name or NDC code for drugs
- The app will use the entered information and fetch details from FDA using the openFDA NDC directory endpoint
- When a typed product name matches multiple FDA-listed products, the app will show the possible matches and let the user choose the exact product before loading full details
- The app will provide a single chatbot that takes on the persona of a pharmaceutical product analyst and answers queries about pharmaceutical products
- If the user asks a question that is not about pharmaceutical products, the chatbot should respond that it cannot answer questions that are not about pharmaceutical products

## Limitations

There will be no user login needed.

## Technical Decisions

- The app should be installable on Hugging Face Spaces
- Use a classic web app experience served by FastAPI
- Use `uv` as the package manager for Python
- Use OpenRouter for the AI calls. An `OPENROUTER_API_KEY` is in `.env` in the project root
- Use Anthropic as the primary chatbot provider and OpenAI as the fallback
- Use the key found in `.env` for `OPENFDA_API_KEY`
- Start and stop server scripts for Mac, PC, Linux in `scripts/`

## Starting Point

This is now an implemented application with a working v1.1 baseline.

## Color Scheme And Navigation

- Use a professional looking color scheme and user experience

## Coding Standards

1. Use latest versions of libraries and idiomatic approaches as of today
2. Keep it simple - NEVER over-engineer, ALWAYS simplify, NO unnecessary defensive programming. No extra features - focus on simplicity.
3. Be concise. Keep README minimal. IMPORTANT: no emojis ever
4. When hitting issues, always identify root cause before trying a fix. Do not guess. Prove with evidence, then fix the root cause.

## Working Documentation

All documents for planning and executing this project will be in the `docs/` directory.
Please review the `docs/PLAN.md` document before proceeding.

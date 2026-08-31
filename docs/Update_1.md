 Pharmaceutical Product Search Web App - updates

## Purpose
Feature updates to create version 1.1 of the FDA Search app

## FDA Search  Changes
- Remove the "Classic web app" and "FDA + 4 model virepoint" text from the header
- In the search text when a typed product name matches with multiple products, bring up the possible matches and allow the user to select the specific product. E.g., "Tylenol" may match with "Tylenol Children", or "Tylenol Cold". in this case, display both and allow the user to select one before showing the rest of the data  
## AI Analysis Changes 
- Remove the 4 llm anaysis feature, and replace it with a single chatbot 
- The chatbot takes on the persona of a pharmaceutical product analyst, and answers queries about pharma products
- Use an Anthropic model for the chatbot, and as a fallback use OpenAI
- If the user asks any question that is not related to pharma products, the chatbot should respond saying that it cannot answer any question that is not about pharmaceutical products 


import { RAGClient } from "../clients/rag_client.js";
import { formatSearchResults } from "../utils/formatter.js";

export const exactSearchTool = {
  name: "exact_search",
  description: "精確條文查詢。當使用者已經知道明確的法律與條號時（例如：勞基法第38條），使用此工具直接精確取得。",
  inputSchema: {
    type: "object",
    properties: {
      query: {
        type: "string",
        description: "精確搜尋查詢句，例如：勞基法第38條"
      }
    },
    required: ["query"]
  }
};

export async function handleExactSearch(args: any, client: RAGClient) {
  const { query } = args;
  const data = await client.exactSearch(query);
  return {
    content: [{
      type: "text",
      text: formatSearchResults(data.results)
    }]
  };
}

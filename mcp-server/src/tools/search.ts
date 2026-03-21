import { RAGClient } from "../clients/rag_client.js";
import { formatSearchResults } from "../utils/formatter.js";

export const semanticSearchTool = {
  name: "semantic_search",
  description: "根據法律問題或關鍵字進行語義搜尋。利用 AI 向量相似度尋找最相關的法條。",
  inputSchema: {
    type: "object",
    properties: {
      query: {
        type: "string",
        description: "法律問題或關鍵字，例如：加班費計算規定"
      },
      top_k: {
        type: "number",
        description: "返回結果數量",
        default: 10
      },
      filter_category: {
        type: "string",
        description: "過濾法律類別（可選）"
      }
    },
    required: ["query"]
  }
};

export async function handleSemanticSearch(args: any, client: RAGClient) {
  const { query, top_k = 10, filter_category } = args;
  const data = await client.semanticSearch(query, top_k, filter_category);
  return {
    content: [{
      type: "text",
      text: formatSearchResults(data.results)
    }]
  };
}

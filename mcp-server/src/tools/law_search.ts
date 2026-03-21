import { RAGClient } from "../clients/rag_client.js";
import { formatSearchResults } from "../utils/formatter.js";

export const lawSearchTool = {
  name: "search_law_by_name",
  description: "法律名稱搜尋。當需要針對『法律名稱』來尋找相關的法律列表時使用。",
  inputSchema: {
    type: "object",
    properties: {
      law_name: {
        type: "string",
        description: "法律名稱或關鍵字，例如：勞動基準法"
      },
      include_abolished: {
        type: "boolean",
        description: "是否包含已廢止的法律",
        default: false
      }
    },
    required: ["law_name"]
  }
};

export async function handleLawSearch(args: any, client: RAGClient) {
  const { law_name, include_abolished = false } = args;
  const data = await client.searchLaw(law_name, include_abolished);
  return {
    content: [{
      type: "text",
      text: formatSearchResults(data.results)
    }]
  };
}

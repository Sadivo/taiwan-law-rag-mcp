import { RAGClient } from "../clients/rag_client.js";
import { formatLawFull } from "../utils/formatter.js";

export const getLawTool = {
  name: "get_law_full_text",
  description: "取得完整法律條文。提供涵蓋該法律所有條文全文的資訊。",
  inputSchema: {
    type: "object",
    properties: {
      law_name: {
        type: "string",
        description: "法律完整名稱，例如：勞動基準法"
      }
    },
    required: ["law_name"]
  }
};

export async function handleGetLaw(args: any, client: RAGClient) {
  const { law_name } = args;
  const data = await client.getLawFullText(law_name);
  return {
    content: [{
      type: "text",
      text: formatLawFull(data.law, data.articles)
    }]
  };
}

import { RAGClient } from "../clients/rag_client.js";
import { formatComparison } from "../utils/formatter.js";

export const compareTool = {
  name: "compare_laws",
  description: "法律比較工具。用來比較多部不同法律在同一個主題/關鍵字下的相關條文差異。",
  inputSchema: {
    type: "object",
    properties: {
      law_names: {
        type: "array",
        items: { type: "string" },
        description: "要比較的法律名稱列表，例如：['民法', '公司法']"
      },
      topic: {
        type: "string",
        description: "比較的主題或關鍵字，例如：股東權利"
      }
    },
    required: ["law_names", "topic"]
  }
};

export async function handleCompare(args: any, client: RAGClient) {
  const { law_names, topic } = args;
  const data = await client.compareLaws(law_names, topic);
  return {
    content: [{
      type: "text",
      text: formatComparison(data.comparison)
    }]
  };
}

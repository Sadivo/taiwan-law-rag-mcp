import { RAGClient } from "../clients/rag_client.js";
import type { ChatResponse, Citation } from "../clients/rag_client.js";

export const askLawQuestionTool = {
  name: "ask_law_question",
  description: "向台灣法律 AI 助理提問，獲得有引用來源的繁體中文回答。",
  inputSchema: {
    type: "object",
    properties: {
      question: {
        type: "string",
        description: "法律問題"
      },
      top_k: {
        type: "number",
        description: "參考條文數量",
        default: 5
      }
    },
    required: ["question"]
  }
};

function formatChatResponse(response: ChatResponse): string {
  let text = response.answer;
  if (response.citations && response.citations.length > 0) {
    text += "\n\n**引用條文：**\n";
    text += response.citations
      .map((c: Citation) => `- ${c.law_name} ${c.article_no}`)
      .join("\n");
  }
  return text;
}

export async function handleAskLawQuestion(args: any, client: RAGClient) {
  const { question, top_k = 5 } = args;
  try {
    const response = await client.chat(question, top_k);
    return {
      content: [{
        type: "text",
        text: formatChatResponse(response)
      }]
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return {
      content: [{
        type: "text",
        text: `無法連線至法律 AI 服務，請確認 API 服務是否正常運行。\n錯誤詳情：${message}`
      }]
    };
  }
}

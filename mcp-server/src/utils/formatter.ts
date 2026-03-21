export interface SearchResult {
    law_name: string;
    law_level: string;
    law_category: string;
    law_url: string;
    article_no: string;
    chapter: string;
    content: string;
    score: number;
    modified_date: string;
}

export function formatSearchResults(results: SearchResult[]): string {
    if (!results || results.length === 0) {
        return "找不到相關法條。";
    }

    let output = `找到 ${results.length} 條相關法條：\n\n`;
    
    results.forEach((result, index) => {
        const chapterStr = result.chapter ? ` (${result.chapter})` : "";
        const scoreStr = result.score ? `\n相關度: ${(result.score).toFixed(2)}` : "";
        
        output += `【${index + 1}】${result.law_name} ${result.article_no}${chapterStr}\n`;
        output += `${result.content}\n`;
        output += `🔗 ${result.law_url}${scoreStr}\n\n`;
    });

    return output;
}

export function formatLawFull(law: any, articles: any[]): string {
    if (!law || !articles) {
        return "找不到該法律文件。";
    }
    
    let output = `# ${law.law_name}\n\n`;
    output += `- 層級：${law.law_level}\n`;
    output += `- 類別：${law.law_category}\n`;
    output += `- 修正日期：${law.modified_date}\n`;
    output += `- 官方連結：${law.law_url}\n`;
    output += `- 狀態：${law.is_abolished ? "已廢止" : "有效"}\n\n`;
    output += `## 條文內容\n\n`;

    let currentChapter = "";
    articles.forEach(article => {
        if (article.chapter && article.chapter !== currentChapter) {
            output += `### ${article.chapter}\n`;
            currentChapter = article.chapter;
        }
        output += `**${article.article_no}**\n${article.content}\n\n`;
    });

    return output;
}

export function formatComparison(comparison: Record<string, any[]>): string {
    if (!comparison || Object.keys(comparison).length === 0) {
        return "找不到比較結果。";
    }
    
    let output = "法律比較結果：\n\n";
    for (const [lawName, articles] of Object.entries(comparison)) {
        output += `### ${lawName}\n`;
        if (articles.length === 0) {
            output += `無相關條文。\n\n`;
            continue;
        }
        
        let currentChapter = "";
        articles.forEach(article => {
            if (article.chapter && article.chapter !== currentChapter) {
                output += `#### ${article.chapter}\n`;
                currentChapter = article.chapter;
            }
            output += `- **${article.article_no}**：${article.content}\n`;
        });
        output += `\n`;
    }
    return output;
}

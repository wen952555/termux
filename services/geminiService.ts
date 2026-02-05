import { GoogleGenAI, Type } from "@google/genai";
import { BotConfig } from "../types";

const SYSTEM_INSTRUCTION = `
You are an expert Python developer and Linux administrator specializing in Termux and Ubuntu (PRoot) environments on Android.
Your task is to generate robust, error-handling Python scripts for Telegram bots.

Context: The user has Termux installed, with Ubuntu (PRoot) installed inside it, and Termux:API.
The script might run in Native Termux OR inside the Ubuntu PRoot.

Best Practices:
1. Use 'python-telegram-bot' (v20+ async).
2. For large bots, prefer modular structure (splitting logic into files), but for this specific single-file generation request, keep it in one file unless the user asks for structure.
3. Check 'effective_user.id' against ADMIN_ID.
4. Detect if running in Termux vs Ubuntu if possible.
5. For Termux:API calls (battery, camera), use full paths if necessary or fallback.
6. IMPORTANCE: All user-facing messages, status reports, logs, and error messages MUST be in CHINESE (Simplified).

When asked to generate the script, return a JSON object containing:
- 'code': The complete, runnable Python source code.
- 'instructions': A markdown string with setup instructions (also in Chinese).
`;

export const generateBotScript = async (config: BotConfig): Promise<{ code: string; instructions: string }> => {
  const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
  
  const prompt = `
    Generate a Telegram Bot script for Termux (with Ubuntu/PRoot support).
    
    Configuration:
    - Bot Token: "${config.botToken || 'YOUR_BOT_TOKEN'}"
    - Admin Chat ID: ${config.chatId || 'YOUR_CHAT_ID'}
    
    Requested Features:
    ${config.features.map(f => `- ${f}`).join('\n')}
    
    Custom Requirements:
    ${config.customPrompt}
    
    Instructions for logic:
    - If "Battery" or "Camera" is requested: Try to use 'termux-battery-status'/'termux-camera-photo'. Warn in comments that these might require running in Native Termux or configuring termux-exec in Ubuntu.
    - If "Audio" or "Video" recording is requested: Always set the duration flag to 30 seconds (e.g., -l 30) unless specified otherwise.
    - If "System Monitor" is requested: Use 'psutil'. If Battery info is also requested, combine it into the System Monitor message instead of a separate command.
    - LANGUAGE REQUIREMENT: The entire Python script interaction (messages sent to Telegram) MUST be in CHINESE.
    
    Structure the code with async/await.
  `;

  try {
    const response = await ai.models.generateContent({
      model: 'gemini-3-flash-preview',
      contents: prompt,
      config: {
        systemInstruction: SYSTEM_INSTRUCTION,
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            code: {
              type: Type.STRING,
              description: "The complete Python script code"
            },
            instructions: {
              type: Type.STRING,
              description: "Markdown instructions for setting up the environment"
            }
          },
          required: ["code", "instructions"]
        }
      }
    });

    const result = JSON.parse(response.text || '{}');
    return {
      code: result.code || "# 生成代码时出错",
      instructions: result.instructions || "未提供说明。"
    };

  } catch (error) {
    console.error("Gemini generation error:", error);
    throw new Error("生成脚本失败，请检查您的 API Key 或网络连接。");
  }
};

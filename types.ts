export interface BotConfig {
  botToken: string;
  chatId: string;
  features: string[];
  customPrompt: string;
}

export interface GeneratedScript {
  code: string;
  instructions: string;
}

export enum ViewState {
  CONFIG = 'CONFIG',
  GENERATING = 'GENERATING',
  RESULT = 'RESULT',
  GUIDE = 'GUIDE'
}

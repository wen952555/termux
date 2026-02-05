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
  GUIDE = 'GUIDE',
  MONITOR = 'MONITOR'
}

export interface SystemStats {
  cpu: number;
  memory: {
    total: number;
    free: number;
    used: number;
    percent: number;
  };
  disk: {
    total: number;
    free: number;
    used: number;
    percent: number;
  };
  uptime: number;
  platform: string;
}


export interface CozeConfig {
  bot_id: string;
  base_url?: string;
}

export interface CozeComponentProps {
  title: string;
  layout: 'inline' | 'drawer' | 'float';
  container: HTMLElement | null;
  lang?: 'zh-CN' | 'en-US';
}

export interface CozeAuth {
  type: 'token' | 'unauth';
  token?: string;
  onRefreshToken?: () => string | Promise<string>;
}

export interface CozeClientOptions {
  config: CozeConfig;
  componentProps: CozeComponentProps;
  auth: CozeAuth;
}

declare global {
  interface Window {
    CozeWebSDK: {
      WebChatClient: new (options: CozeClientOptions) => any;
    };
  }
}

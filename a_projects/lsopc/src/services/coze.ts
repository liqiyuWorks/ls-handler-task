
import { APP_CONFIG } from '../../constants';

export interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
    type: 'answer' | 'function_call' | 'tool_response' | 'follow_up';
}

export interface ChatStreamResponse {
    event: string;
    data: any;
}

export const chatWithCoze = async (
    messages: { role: string; content: string; content_type: string }[],
    onMessage: (chunk: string) => void,
    onCompleted: () => void,
    onError: (error: any) => void,
    botId?: string
) => {
    try {
        const response = await fetch('/coze-api/v3/chat', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${APP_CONFIG.COZE_TOKEN}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                bot_id: botId || APP_CONFIG.COZE_BOT_ID,
                user_id: 'user_' + Math.random().toString(36).substring(7),
                stream: true,
                auto_save_history: true,
                additional_messages: messages
            }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();

        if (!reader) {
            throw new Error('Response body is null');
        }

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('event:')) {
                    const eventType = line.replace('event:', '').trim();
                    // We are primarily interested in 'conversation.message.delta' or 'conversation.message.completed'
                    // logic will be handled in data processing
                    (window as any).currentEventType = eventType;
                } else if (line.startsWith('data:')) {
                    const dataStr = line.replace('data:', '').trim();
                    try {
                        const data = JSON.parse(dataStr);
                        const eventType = (window as any).currentEventType;

                        if (eventType === 'conversation.message.delta') {
                            if (data.type === 'answer') {
                                onMessage(data.content);
                            }
                        } else if (eventType === 'conversation.chat.completed') {
                            onCompleted();
                        }
                    } catch (e) {
                        // Ignore parse errors for non-JSON data lines (like [DONE])
                    }
                }
            }
        }
    } catch (error) {
        onError(error);
    }
};

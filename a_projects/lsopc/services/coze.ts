
import { APP_CONFIG } from '../constants';

const API_BASE = 'https://api.coze.cn/open_api/v2';

export const chatWithCoze = async (
    messages: any[],
    onChunk: (chunk: string) => void,
    onFinish: () => void,
    onError: (error: any) => void,
    botId?: string
) => {
    const token = APP_CONFIG.COZE_TOKEN; // Ensure this is defined in constants or env
    if (!token) {
        onError(new Error('Coze API Token not configured'));
        return;
    }

    const endpoint = `${API_BASE}/chat`;
    const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
    };

    const body = JSON.stringify({
        bot_id: botId || APP_CONFIG.COZE_BOT_ID,
        user: 'user_123', // Demo user ID
        query: messages[messages.length - 1].content,
        stream: true,
        chat_history: messages.slice(0, -1).map(m => ({
            role: m.role,
            content: m.content,
            content_type: 'text'
        }))
    });

    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers,
            body,
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.msg || `HTTP Error ${response.status}`);
        }

        if (!response.body) throw new Error('No response body');

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.startsWith('data:')) {
                    const dataStr = line.slice(5).trim();
                    if (!dataStr || dataStr === '[DONE]') continue;
                    try {
                        const data = JSON.parse(dataStr);
                        if (data.event === 'message' && data.message && data.message.type === 'answer') {
                            onChunk(data.message.content);
                        } else if (data.event === 'conversation.message.delta' && data.content) {
                            onChunk(data.content);
                        }
                    } catch (e) {
                        // ignore parse errors
                    }
                }
            }
        }
        onFinish();
    } catch (error) {
        onError(error);
    }
};

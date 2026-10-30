export const parseMessages = (message: string, type: string) => {
    try {
        if (message == '\n') {
            return '\n'
        }
        if (type === 'Qwen3') {
            // Qwen3 SSE：一个 chunk 可能包含 0 个、1 个或多个完整帧，
            // 每帧形如：
            //   id:40\n
            //   event:result\n
            //   :HTTP_STATUS/200\n
            //   {...json...}\n\n
            // 取所有以 { 开头的行，逐行 JSON.parse，拼接其中的文本增量。
            let out = ''
            for (const line of message.split(/\r?\n/)) {
                const trimmed = line.trim()
                if (!trimmed.startsWith('{')) continue
                try {
                    const body = JSON.parse(trimmed)
                    const choice = body?.output?.choices?.[0]
                    const content = choice?.message?.content
                    if (Array.isArray(content)) {
                        for (const c of content) {
                            if (c && typeof c.text === 'string') out += c.text
                        }
                    } else if (typeof content === 'string') {
                        out += content
                    }
                } catch {
                    // 半截 JSON：忽略，等下一帧补齐
                }
            }
            return out
        }

        const parts = message.split('HTTP_STATUS/200')
        if (parts.length > 1) {
            message = parts[1]
        }
        const messageBody = JSON.parse(message);
        if (type === 'OpenAi') {
            if (!messageBody.choices || messageBody.choices.length === 0) {
                return ''
            }
            if (!messageBody.choices[0].delta || !messageBody.choices[0].delta.content) {
                return ''
            }
            return messageBody.choices[0].delta.content
        } else if (type === 'Qwen') {
            if (!messageBody.output) {
                return ''
            }
            if (!messageBody.output.choices || messageBody.output.choices.length === 0) {
                return ''
            }
            return messageBody.output.choices[0].message.content
        }
        return ''
    } catch (error) {
        console.error(error)
        return ''
    }
}
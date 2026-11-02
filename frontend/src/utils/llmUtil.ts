/**
 * 解析 SSE 流式数据。传入的 message 是**所有 chunk 拼接后的完整字符串**，
 * 因为 TCP 分片可能把一帧 JSON 拆到多个 chunk 里，必须拼接后再按行解析。
 *
 * 一个 chunk 里可能有 0 / 1 / 多帧完整数据，也可能末尾带半截 JSON（流式尚未结束）。
 */
export const parseMessages = (message: string, type: string): string => {
    if (!message) {
        return ''
    }
    if (message === '\n') {
        return '\n'
    }

    // 把所有行里能识别出的 JSON 行收集起来，逐个尝试 parse。
    // 不完整的 JSON 行直接跳过（等下一帧补齐后重新拼接解析）。
    let out = ''
    console.log(message);
    for (const rawLine of message.split(/\r?\n/)) {
        const line = stripSsePrefix(rawLine).trimStart()
        if (!line.startsWith('{')) {
            continue
        }
        let body: any
        try {
            body = JSON.parse(line)
        } catch {
            continue
        }
        if (!body) {
            continue
        }
        if (type === 'OpenAi') {
            out += openAiParser(body)
        } else if (type === 'Qwen') {
            out += qwenParser(body)
        }
    }
    return out
}

const openAiParser = (body: any) => {
    const delta = body?.choices?.[0]?.delta
    if (delta && typeof delta.content === 'string') {
        return delta.content
    }
    return ""
}

const qwenParser = (body: any) => {
    // Qwen / Qwen3: {"output":{"choices":[{"message":{"content": [...] 或 "..."}}]}}
    const content = body?.output?.choices?.[0]?.message?.content
    if (Array.isArray(content)) {
        for (const c of content) {
            if (c && typeof c.text === 'string') {
                return c.text
            }
        }
    } else if (typeof content === 'string') {
        return content;
    }
    return ""
}

/**
 * 去掉 SSE 行前缀，取出可能的 JSON 部分：
 *   data: {...}      -> {...}
 *   :HTTP_STATUS/200 -> ''
 *   id:40            -> ''
 *   event:result     -> ''
 */
const stripSsePrefix = (line: string): string => {
    const prefixSet = ['data:'];
    for (const prefix of prefixSet) {
        if (line.startsWith(prefix)) {
            // 切掉 data:，然后只去掉前缀后面单个空格，不要直接全量trim
            const raw = line.slice(prefix.length);
            return raw[0] === ' ' ? raw.slice(1) : raw;
        }
    }

    // 本身就是json行（极少情况）直接返回
    const t = line.trimStart();
    if (t.startsWith('{')) {
        return line;
    } else {
        // 去除第一个{前的字符
        return line.slice(line.indexOf('{'));
    }
    return '';
}


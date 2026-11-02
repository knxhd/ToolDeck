/**
 * 合并后的流式结果：正文与思考过程（reasoning_content）分开保存，
 * 便于 UI 区分渲染（思考过程默认弱化展示，可折叠）。
 */
export interface MergedSseResult {
    content: string
    reasoning: string
}

/**
 * 解析 SSE 流式数据。传入的 message 是**所有 chunk 拼接后的完整字符串**，
 * 因为 TCP 分片可能把一帧 JSON 拆到多个 chunk 里，必须拼接后再按行解析。
 *
 * 一个 chunk 里可能有 0 / 1 / 多帧完整数据，也可能末尾带半截 JSON（流式尚未结束）。
 */
export const parseMessages = (message: string, type: string): MergedSseResult => {
    const result: MergedSseResult = { content: '', reasoning: '' }
    if (!message) {
        return result
    }
    if (message === '\n') {
        return { content: '\n', reasoning: '' }
    }

    // 把所有行里能识别出的 JSON 行收集起来，逐个尝试 parse。
    // 不完整的 JSON 行直接跳过（等下一帧补齐后重新拼接解析）。
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
        let part: MergedSseResult | null = null
        if (type === 'OpenAi') {
            part = openAiParser(body)
        } else if (type === 'Qwen') {
            part = qwenParser(body)
        }
        if (part) {
            result.content += part.content
            result.reasoning += part.reasoning
        }
    }
    return result
}

/**
 * 从 content / reasoning_content 这类字段中取出文本。
 * 兼容字符串、字符串数组以及 [{ text: '...' }] 两种形式。
 */
const pickText = (value: any): string => {
    if (typeof value === 'string') {
        return value
    }
    if (Array.isArray(value)) {
        let out = ''
        for (const item of value) {
            if (typeof item === 'string') {
                out += item
            } else if (item && typeof item.text === 'string') {
                out += item.text
            }
        }
        return out
    }
    return ''
}

/** 思考过程字段在不同厂商下的命名：reasoning_content / reasoning / reasoning_text */
const pickReasoning = (source: any): string => pickText(
    source?.reasoning_content ?? source?.reasoning ?? source?.reasoning_text,
)

const openAiParser = (body: any): MergedSseResult => {
    // 流式为 choices[0].delta，非流式为 choices[0].message，两者字段一致
    const delta = body?.choices?.[0]?.delta ?? body?.choices?.[0]?.message
    if (!delta) {
        return { content: '', reasoning: '' }
    }
    return {
        content: pickText(delta.content),
        reasoning: pickReasoning(delta),
    }
}

const qwenParser = (body: any): MergedSseResult => {
    // Qwen / Qwen3: {"output":{"choices":[{"message":{"content": [...] 或 "...", "reasoning_content": "..."}}]}}
    const message = body?.output?.choices?.[0]?.message
        ?? body?.output?.choices?.[0]?.delta
        ?? body?.choices?.[0]?.delta
    if (!message) {
        return { content: '', reasoning: '' }
    }
    return {
        content: pickText(message.content),
        reasoning: pickReasoning(message),
    }
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


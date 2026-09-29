export const parseMessages = (message, type) => {
    try {
        if (message == '\n') {
            return '\n'
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
        } else if (type === 'Qwen3') {
            if (!messageBody.output) {
                return ''
            }
            if (!messageBody.output.choices || messageBody.output.choices.length === 0) {
                return ''
            }
            return messageBody.output.choices[0].message.content[0].text
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
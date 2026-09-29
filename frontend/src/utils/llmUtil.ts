export const parseMessages = (message, type) => {
    try {
        if (message == '\n') {
            return '\n'
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
            return messageBody.output.choices[0].message.content[0].text
        } else if (type === 'Qwen') {
            return messageBody.output.choices[0].message.content
        }
    } catch (error) {
        console.error(error)
        return ''
    }
 
}
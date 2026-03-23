export function addMessage(sender, text){

    const chatBox = document.getElementById("chat-box");

    const div = document.createElement("div");

    div.className = sender;

    div.innerText = text;

    chatBox.appendChild(div);

    chatBox.scrollTop = chatBox.scrollHeight;
}

export function createBotMessage(){

    const chatBox = document.getElementById("chat-box");

    const div = document.createElement("div");

    div.className = "bot";

    div.innerText = "";

    chatBox.appendChild(div);

    return div;
}

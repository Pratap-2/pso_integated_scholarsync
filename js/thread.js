import { setThreadID } from "./config.js";
import { loadThreads } from "./history.js";

export function generateThreadID(){
    return "thread_" + crypto.randomUUID();
}

export function newChat(){

    const id = generateThreadID();

    setThreadID(id);

    document.getElementById("chat-box").innerHTML = "";

    loadThreads();

}

export function switchThread(){

    const dropdown = document.getElementById("thread-list");

    const selectedThread = dropdown.value;

    if(!selectedThread) return;

    setThreadID(selectedThread);

    import("./history.js").then(module => {
        module.loadHistory();
    });

}

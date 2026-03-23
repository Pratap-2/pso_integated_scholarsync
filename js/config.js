export const API_BASE = "http://127.0.0.1:8000";

export let thread_id = localStorage.getItem("thread_id");

export function setThreadID(id){
    thread_id = id;
    localStorage.setItem("thread_id", id);
}

export function getThreadID(){
    return thread_id;
}

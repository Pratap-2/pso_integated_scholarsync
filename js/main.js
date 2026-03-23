import { getThreadID, setThreadID } from "./config.js";
import { generateThreadID, newChat, switchThread } from "./thread.js";
import { sendMessage } from "./chat.js?v=14";
import { loadHistory, loadThreads, deleteCurrentThread } from "./history.js";
import { initSidebarSync } from "./sidebar.js";

// Initialize application after DOM is ready
document.addEventListener("DOMContentLoaded", async () => {

try {

    // Ensure thread exists
    if (!getThreadID()) {
        setThreadID(generateThreadID());
    }

    // Initialize sidebar history sync
    initSidebarSync();

    // Load all threads from backend
    await loadThreads();

    // Load current thread chat history
    await loadHistory();

    // Setup Enter key send handler
    const messageInput = document.getElementById("message");

    if (messageInput) {

        messageInput.addEventListener("keypress", (event) => {

            if (event.key === "Enter") {
                event.preventDefault();
                sendMessage();
            }

        });

    }

    console.log("App initialized successfully");

} catch (error) {

    console.error("Initialization failed:", error);

}


});

// Expose functions globally for HTML usage
window.sendMessage = sendMessage;
window.newChat = newChat;
window.switchThread = switchThread;
window.deleteCurrentThread = deleteCurrentThread;
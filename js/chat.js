import { API_BASE, getThreadID } from "./config.js";
import { addMessage, createBotMessage } from "./ui.js";

export async function sendMessage(){

    const input = document.getElementById("message");

    const msg = input.value.trim();

    if(msg === "") return;

    addMessage("user", msg);

    input.value = "";

    const botDiv = createBotMessage();

    try{

        const response = await fetch(`${API_BASE}/chat-stream`, {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                message: msg,
                thread_id: getThreadID()
            })

        });

        const reader = response.body.getReader();

        const decoder = new TextDecoder();

        while(true){

            const { done, value } = await reader.read();

            if(done) break;

            botDiv.innerText += decoder.decode(value);

        }

        // Post-process the final text for dynamic UI injection
        let finalTxt = botDiv.innerText;

        // Redirect Interceptor
        if (finalTxt.includes("[REDIRECT:assignment_solver]")) {
            window.location.href = "assignment_solver.html";
            return;
        }
        if (finalTxt.includes("[REDIRECT:materials]")) {
            window.location.href = "material_view.html";
            return;
        }
        if (finalTxt.includes("[REDIRECT:study_planner]")) {
            window.location.href = "index.html"; // The main dashboard holds the study timeline
            return;
        }

        // Extract ui_materials JSON block
        const matRegex = /```ui_materials\s+([\s\S]*?)```/;
        const matchMat = finalTxt.match(matRegex);

        if (matchMat) {
            let jsonStr = matchMat[1].trim();
            try {
                let materials = JSON.parse(jsonStr);
                let cardsHtml = '<div class="chat-native-list">';
                materials.forEach(m => {
                    let subject = m.subject || "Course Material";
                    let title = m.title || "Untitled";
                    let desc = m.description || "";
                    let link = m.link || m.materialLink || "#";
                    
                    cardsHtml += `
                    <div class="cn-card-horiz">
                      <div class="cnc-right">
                        <div class="cnc-top">
                          <span class="cnc-subject">
                            <svg width="10" height="10" fill="none" viewBox="0 0 24 24" style="margin-right:2px"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                            ${subject}
                          </span>
                        </div>
                        <div class="cnc-title" title="${title}">${title}</div>
                        ${desc ? `<div class="cnc-desc">${desc}</div>` : ""}
                        <div class="cnc-footer">
                          <a href="${link}" class="cnc-btn" target="_blank">
                            Open Material
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                          </a>
                        </div>
                      </div>
                    </div>`;
                });
                cardsHtml += '</div>';

                let cleanTxt = finalTxt.replace(matRegex, "").trim();
                let buttonsHtml = `
                <div style="margin-top:14px; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 12px;">
                  <p style="font-size: 13.5px; margin-bottom: 10px; color: #d0e8ff;">Do you want to open your materials dashboard?</p>
                  <div style="display:flex; gap: 8px;">
                    <button class="cnc-btn" style="padding: 6px 16px; border:none; color: var(--electric);" onclick="if(window.parent && window.parent.openMaterials){window.parent.openMaterials()}else{window.location.href='material_view.html'}">Yes, open dashboard ↗</button>
                    <button style="padding: 6px 16px; background:transparent; border:1px solid rgba(255,255,255,0.2); color:#a0b8d0; border-radius: 6px; cursor: pointer; transition: all 0.2s;" onclick="this.parentElement.parentElement.style.opacity=0.5; this.disabled=true;" onmouseover="this.style.background='rgba(255,255,255,0.05)'" onmouseout="this.style.background='transparent'">No, thanks</button>
                  </div>
                </div>`;
                botDiv.innerHTML = cardsHtml + (cleanTxt ? `<div style='margin-top:12px; line-height:1.5; font-size:14px;'>${cleanTxt.replace(/\n/g, '<br>')}</div>` : '') + buttonsHtml;
                const chatBox = document.getElementById("chat-box");
                if (chatBox) chatBox.scrollTop = chatBox.scrollHeight;
            } catch(e) {
                console.error("Failed to parse materials JSON", e);
            }
        }

        // Extract ui_assignments JSON block
        const asgRegex = /```ui_assignments\s+([\s\S]*?)```/;
        const matchAsg = finalTxt.match(asgRegex);
        
        if (matchAsg) {
            let jsonStr = matchAsg[1].trim();
            try {
                let assignments = JSON.parse(jsonStr);
                let cardsHtml = '<div class="chat-native-list">';
                assignments.forEach(a => {
                    let subject = a.subject || "Assignment";
                    let title = a.title || "Untitled";
                    let desc = a.description || "";
                    let doc = a.assignmentDoc || a.link || "#";
                    let deadlineStr = a.deadline ? `Due: ${new Date(a.deadline).toLocaleDateString()}` : "No deadline";

                    let isLinkValid = doc !== "#";
                    let targetAttr = isLinkValid ? 'target="_blank"' : '';
                    let hrefAttr = isLinkValid ? doc : 'assignment_solver.html';

                    cardsHtml += `
                    <div class="cn-card-horiz cn-asg">
                      <div class="cnc-right">
                        <div class="cnc-top">
                          <span class="cnc-subject">
                            <svg width="10" height="10" fill="none" viewBox="0 0 24 24" style="margin-right:2px"><path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
                            ${subject}
                          </span>
                          <span class="cnc-deadline">${deadlineStr}</span>
                        </div>
                        <div class="cnc-title" title="${title}">${title}</div>
                        ${desc ? `<div class="cnc-desc">${desc}</div>` : ""}
                        <div class="cnc-footer">
                          <a href="${hrefAttr}" class="cnc-btn cnc-btn-asg" ${targetAttr}>
                            View Assignment
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                          </a>
                        </div>
                      </div>
                    </div>`;
                });
                cardsHtml += '</div>';

                let cleanTxt = finalTxt.replace(asgRegex, "").trim();
                let buttonsHtml = `
                <div style="margin-top:14px; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 12px;">
                  <p style="font-size: 13.5px; margin-bottom: 10px; color: #d0e8ff;">Do you want to know about your assignment in detail?</p>
                  <div style="display:flex; gap: 8px;">
                    <button class="cnc-btn cnc-btn-asg" style="padding: 6px 16px; border:none;" onclick="if(window.parent && window.parent.openAssignmentSolver){window.parent.openAssignmentSolver()}else{window.location.href='assignment_solver.html'}">Yes, open solver ↗</button>
                    <button style="padding: 6px 16px; background:transparent; border:1px solid rgba(255,255,255,0.2); color:#a0b8d0; border-radius: 6px; cursor: pointer; transition: all 0.2s;" onclick="this.parentElement.parentElement.style.opacity=0.5; this.disabled=true;" onmouseover="this.style.background='rgba(255,255,255,0.05)'" onmouseout="this.style.background='transparent'">No, thanks</button>
                  </div>
                </div>`;
                botDiv.innerHTML = cardsHtml + (cleanTxt ? `<div style='margin-top:12px; line-height:1.5; font-size:14px;'>${cleanTxt.replace(/\n/g, '<br>')}</div>` : '') + buttonsHtml;
                const chatBox = document.getElementById("chat-box");
                if (chatBox) chatBox.scrollTop = chatBox.scrollHeight;
            } catch(e) {
                console.error("Failed to parse assignments JSON", e);
            }
        }

    }
    catch(error){

        botDiv.innerText = "Error connecting to server";

        console.error(error);

    }

}

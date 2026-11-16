
let currentChat = null;


// =================================
// API CONNECTION
// =================================

async function api(url, options = {}) {

    const response = await fetch(url, {
        headers: {
            "Content-Type": "application/json"
        },
        ...options
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || "Something went wrong.");
    }

    return data;
}


// =================================
// LOGIN AND REGISTRATION
// =================================

function showAuth(action) {

    const box = document.getElementById("authBox");

    box.style.display = "block";
    box.dataset.action = action;

    document.getElementById("authTitle").innerText =
        action === "login" ? "Login" : "Create Account";

    document.getElementById("authError").innerText = "";
}


async function submitAuth() {

    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

    try {

        await api("/auth", {
            method: "POST",

            body: JSON.stringify({
                username: username,
                password: password,
                action: document.getElementById("authBox").dataset.action
            })
        });

        await openApplication();

    } catch (error) {

        document.getElementById("authError").innerText =
            error.message;
    }
}


// =================================
// GUEST LOGIN
// =================================

function guestLogin() {
    window.location.href = "/guest";
}

function logout() {
    window.location.href = "/logout";
}


// =================================
// OPEN APPLICATION
// =================================

async function openApplication() {

    document.getElementById("welcome").style.display = "none";

    document.getElementById("application").style.display = "flex";

    await loadHistory();

    if (!currentChat) {
        await newChat();
    }
}


// =================================
// CHAT HISTORY
// =================================

async function loadHistory() {

    const chats = await api("/api/chats");

    const history = document.getElementById("history");

    history.innerHTML = "";

    chats.forEach(chat => {

        const item = document.createElement("div");

        item.className = "chat-item";

        if (chat.id === currentChat) {
            item.classList.add("active");
        }

        const title = document.createElement("span");

        title.textContent = chat.title;

        title.onclick = () => selectChat(chat.id);

        const deleteButton = document.createElement("button");

        deleteButton.textContent = "×";

        deleteButton.title = "Delete conversation";

        deleteButton.onclick = (event) => {

            event.stopPropagation();

            deleteChat(chat.id);
        };

        item.appendChild(title);

        item.appendChild(deleteButton);

        history.appendChild(item);

    });
}


// =================================
// NEW CHAT
// =================================

async function newChat() {

    const data = await api("/api/new", {
        method: "POST"
    });

    currentChat = data.id;

    document.getElementById("messages").innerHTML = "";

    addMessage(
        "Hello! I'm Aura 🌸. How can I help you today?",
        "bot"
    );

    await loadHistory();
}


// =================================
// PREVIOUS CHAT
// =================================

async function selectChat(id) {

    try {

        currentChat = id;

        const messages = await api("/api/messages/" + id);

        document.getElementById("messages").innerHTML = "";

        messages.forEach(message => {

            addMessage(
                message.content,
                message.role === "user" ? "user" : "bot"
            );

        });

        await loadHistory();

    } catch (error) {

        showStatus(error.message);
    }
}


// =================================
// DELETE CHAT
// =================================

async function deleteChat(id) {

    if (!confirm("Are you sure you want to delete this chat?")) {
        return;
    }

    try {

        await api("/api/delete/" + id, {
            method: "DELETE"
        });

        if (currentChat === id) {
            currentChat = null;
        }

        await loadHistory();

        if (!currentChat) {
            await newChat();
        }

    } catch (error) {

        showStatus(error.message);
    }
}


// =================================
// DISPLAY CHAT MESSAGES
// =================================

function addMessage(text, type) {

    const messages = document.getElementById("messages");

    const div = document.createElement("div");

    div.className = "message " + type;

    div.textContent = text;

    messages.appendChild(div);

    messages.scrollTop = messages.scrollHeight;
}


// =================================
// SEND MESSAGE
// =================================

async function sendMessage() {

    const input = document.getElementById("message");

    const message = input.value.trim();

    if (!message) {
        return;
    }

    if (!currentChat) {
        await newChat();
    }

    input.value = "";

    addMessage(message, "user");

    showStatus("Aura is thinking...");

    try {

        const data = await api("/api/chat", {

            method: "POST",

            body: JSON.stringify({
                chat_id: currentChat,
                message: message
            })

        });

        addMessage(data.reply, "bot");

        await loadHistory();

        showStatus("");

    } catch (error) {

        showStatus(error.message);
    }
}


// =================================
// MOOD CHECKER
// =================================

async function checkMood(mood) {

    try {

        const data = await api("/api/mood", {

            method: "POST",

            body: JSON.stringify({
                mood: mood
            })

        });

        document.getElementById("moodResult").innerText =
            "💜 " + data.suggestion;

    } catch (error) {

        showStatus(error.message);
    }
}


// =================================
// STATUS MESSAGE
// =================================

function showStatus(message) {

    document.getElementById("status").innerText = message;
}


// =================================
// START APPLICATION
// =================================

async function startApplication() {
    try {
        const response = await api("/api/session");

        if (response.logged_in) {
            await openApplication();
        } else {
            document.getElementById("welcome").style.display = "flex";
            document.getElementById("application").style.display = "none";
        }

    } catch (error) {
        console.log(error.message);
    }
}

startApplication();
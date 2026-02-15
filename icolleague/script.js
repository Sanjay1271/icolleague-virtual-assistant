function sendMessage() {
    const messageInput = document.getElementById("message");
    const chatBox = document.getElementById("chat-box");

    let message = messageInput.value;

    chatBox.innerHTML += "<p><b>You:</b> " + message + "</p>";

    fetch("/chat", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ message: message })
    })
    .then(response => response.json())
    .then(data => {
        chatBox.innerHTML += "<p><b>Bot:</b> " + data.response + "</p>";
        messageInput.value = "";
    });
}

function clearChat() {
    const chatBox = document.getElementById("chat-box");
    chatBox.innerHTML = "";
}

document.getElementById("message").
addEventListener("keypress", function(event) {
    if (event.key === "Enter") {
        event.preventDefault();
        sendMessage();
    }
});

document.getElementById("clear-button").addEventListener("click", clearChat);

document.getElementById("send-button").addEventListener("click", sendMessage);

document.getElementById("userInput").addEventListener("keypress", function(event) {
    if (event.key === "Enter") {
        event.preventDefault();
        sendMessage();
    }
});


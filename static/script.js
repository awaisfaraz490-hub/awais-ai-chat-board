const API_URL = "";


const pdfInput =
    document.getElementById("pdfInput");

const pdfList =
    document.getElementById("pdfList");

const chatMessages =
    document.getElementById("chatMessages");

const questionInput =
    document.getElementById("questionInput");

const sendBtn =
    document.getElementById("sendBtn");

const clearChatBtn =
    document.getElementById("clearChatBtn");

const status =
    document.getElementById("status");


// =========================
// LOAD PDFs
// =========================

async function loadPDFs() {

    try {

        const response =
            await fetch(
                `${API_URL}/pdfs`,
                {
                    credentials: "same-origin"
                }
            );

        const data =
            await response.json();

        displayPDFs(
            data.pdfs
        );

    }

    catch (error) {

        console.error(
            "Could not load PDFs:",
            error
        );

    }

}


// =========================
// DISPLAY PDFs
// =========================

function displayPDFs(
    pdfs
) {

    pdfList.innerHTML = "";


    if (!pdfs.length) {

        pdfList.innerHTML =
            `<p class="empty-text">
                No PDFs uploaded
            </p>`;

        return;

    }


    pdfs.forEach(
        pdf => {

            const item =
                document.createElement(
                    "div"
                );

            item.className =
                "pdf-item";


            const lowerName =
                pdf.filename.toLowerCase();

            const isImage =
                [".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"]
                    .some(ext => lowerName.endsWith(ext));

            const icon =
                isImage ? "🖼️" : "📄";


            item.innerHTML = `

                <input
                    type="checkbox"
                    class="pdf-checkbox"
                    value="${pdf.uuid}"
                    checked
                >

                <span
                    class="pdf-name"
                    title="${pdf.filename}"
                >
                    ${icon} ${pdf.filename}
                </span>

                <button
                    class="delete-pdf"
                    onclick="deletePDF('${pdf.uuid}')"
                >
                    ×
                </button>

            `;


            pdfList.appendChild(
                item
            );

        }
    );

}


// =========================
// GET SELECTED PDFs
// =========================

function getSelectedPDFs() {

    const checkboxes =
        document.querySelectorAll(
            ".pdf-checkbox:checked"
        );


    return Array.from(
        checkboxes
    ).map(
        checkbox =>
            checkbox.value
    );

}


// =========================
// UPLOAD PDF
// =========================

pdfInput.addEventListener(
    "change",
    async function () {

        const file =
            this.files[0];


        if (!file) {

            return;

        }


        const allowedExtensions = [
            ".pdf", ".txt", ".md",
            ".png", ".jpg", ".jpeg",
            ".webp", ".gif", ".bmp"
        ];

        const lowerName =
            file.name.toLowerCase();

        const isAllowed =
            allowedExtensions.some(
                ext => lowerName.endsWith(ext)
            );

        if (!isAllowed) {

            alert(
                "Please select a PDF, TXT, or image (PNG/JPG/etc.) file."
            );

            return;

        }


        const formData =
            new FormData();


        formData.append(
            "file",
            file
        );


        try {

            status.textContent =
                "● Uploading...";


            const response =
                await fetch(
                    `${API_URL}/upload`,
                    {
                        method: "POST",

                        credentials: "same-origin",

                        body: formData
                    }
                );


            const data =
                await response.json();


            if (!response.ok) {

                throw new Error(
                    data.detail ||
                    "Upload failed."
                );

            }


            status.textContent =
                "● Online";


            alert(
                "File uploaded successfully!"
            );


            await loadPDFs();

        }

        catch (error) {

            status.textContent =
                "● Error";


            alert(
                error.message
            );

        }


        this.value = "";

    }
);


// =========================
// DELETE PDF
// =========================

async function deletePDF(
    uuid
) {

    const confirmed =
        confirm(
            "Delete this PDF?"
        );


    if (!confirmed) {

        return;

    }


    try {

        const response =
            await fetch(
                `${API_URL}/pdfs/${uuid}`,
                {
                    method: "DELETE",

                    credentials: "same-origin"
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Delete failed."
            );

        }


        await loadPDFs();

    }

    catch (error) {

        alert(
            error.message
        );

    }

}


// =========================
// SEND QUESTION
// =========================

async function sendQuestion() {

    const question =
        questionInput.value.trim();


    if (!question) {

        return;

    }


    const selectedPDFs =
        getSelectedPDFs();


    if (selectedPDFs.length === 0) {

        const usePDF =
            confirm(
                "No file is selected. Ask General AI instead?"
            );


        if (!usePDF) {

            return;

        }

    }


    const welcome =
        document.querySelector(
            ".welcome-message"
        );


    if (welcome) {

        welcome.remove();

    }


    addMessage(
        "user",
        question
    );


    questionInput.value = "";

    sendBtn.disabled = true;

    status.textContent =
        "● Thinking...";


    try {

        const response =
            await fetch(
                `${API_URL}/ask`,
                {
                    method: "POST",

                    credentials: "same-origin",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        question:
                            question,

                        use_pdfs:
                            selectedPDFs.length > 0,

                        pdf_uuids:
                            selectedPDFs

                    })

                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "AI request failed."
            );

        }


        addMessage(
            "ai",
            data.answer,
            data.sources
        );


        status.textContent =
            "● Online";

    }

    catch (error) {

        addMessage(
            "ai",
            "Sorry, something went wrong: " +
            error.message
        );


        status.textContent =
            "● Error";

    }


    sendBtn.disabled = false;

    questionInput.focus();

}


// =========================
// ADD MESSAGE
// =========================

function addMessage(
    type,
    text,
    sources = []
) {

    const message =
        document.createElement(
            "div"
        );


    message.className =
        `message ${type}`;


    const content =
        document.createElement(
            "div"
        );


    content.className =
        "message-content";


    content.textContent =
        text;


    message.appendChild(
        content
    );


    if (
        type === "ai" &&
        sources &&
        sources.length
    ) {

        const sourceDiv =
            document.createElement(
                "div"
            );


        sourceDiv.className =
            "sources";


        sourceDiv.innerHTML =
            "<strong>Sources:</strong>";


        sources.forEach(
            source => {

                const sourceItem =
                    document.createElement(
                        "span"
                    );


                sourceItem.className =
                    "source-item";


                sourceItem.textContent =
                    "📄 " + source;


                sourceDiv.appendChild(
                    sourceItem
                );

            }
        );


        content.appendChild(
            sourceDiv
        );

    }


    chatMessages.appendChild(
        message
    );


    chatMessages.scrollTop =
        chatMessages.scrollHeight;

}


// =========================
// SEND BUTTON
// =========================

sendBtn.addEventListener(
    "click",
    sendQuestion
);


// =========================
// ENTER KEY
// =========================

questionInput.addEventListener(
    "keydown",
    function (event) {

        if (
            event.key === "Enter" &&
            !event.shiftKey
        ) {

            event.preventDefault();

            sendQuestion();

        }

    }
);


// =========================
// CLEAR CHAT
// =========================

clearChatBtn.addEventListener(
    "click",
    async function () {

        const confirmed =
            confirm(
                "Clear all chat history?"
            );


        if (!confirmed) {

            return;

        }


        try {

            const response =
                await fetch(
                    `${API_URL}/chat-history`,
                    {
                        method: "DELETE",

                        credentials: "same-origin"
                    }
                );


            const data =
                await response.json();


            if (!response.ok) {

                throw new Error(
                    data.detail ||
                    "Could not clear chat."
                );

            }


            chatMessages.innerHTML = `

                <div class="welcome-message">

                    <div class="welcome-icon">
                        🤖
                    </div>

                    <h2>
                        Hello! 👋
                    </h2>

                    <p>
                        Upload a PDF, image, or text
                        file and ask me anything
                        about it.
                    </p>

                </div>

            `;

        }

        catch (error) {

            alert(
                error.message
            );

        }

    }
);


// =========================
// VOICE INPUT
// =========================

const micBtn =
    document.getElementById("micBtn");

const voiceLangBtn =
    document.getElementById("voiceLangBtn");

const SpeechRecognitionAPI =
    window.SpeechRecognition ||
    window.webkitSpeechRecognition;


const voiceLanguages = [
    {
        code: "en-US",
        label: "🎙️ English"
    },

    {
        code: "ur-PK",
        label: "🎙️ اردو"
    }
];


let voiceLangIndex = 0;

let recognition = null;

let isListening = false;


if (!SpeechRecognitionAPI) {

    if (micBtn)
        micBtn.style.display = "none";

    if (voiceLangBtn)
        voiceLangBtn.style.display = "none";

}

else {

    recognition =
        new SpeechRecognitionAPI();

    recognition.continuous = false;

    recognition.interimResults = true;

    recognition.lang =
        voiceLanguages[
            voiceLangIndex
        ].code;


    recognition.addEventListener(
        "result",
        function (event) {

            let transcript = "";

            for (
                let i = 0;
                i < event.results.length;
                i++
            ) {

                transcript +=
                    event.results[i][0].transcript;

            }

            questionInput.value =
                transcript;

        }
    );


    recognition.addEventListener(
        "end",
        function () {

            isListening = false;

            micBtn.classList.remove(
                "listening"
            );

            status.textContent =
                "● Online";

        }
    );


    recognition.addEventListener(
        "error",
        function (event) {

            isListening = false;

            micBtn.classList.remove(
                "listening"
            );

            status.textContent =
                "● Online";


            if (
                event.error === "not-allowed"
            ) {

                alert(
                    "Microphone access denied. Please allow microphone permission and try again."
                );

            }

        }
    );


    micBtn.addEventListener(
        "click",
        function () {

            if (isListening) {

                recognition.stop();

                return;

            }


            recognition.lang =
                voiceLanguages[
                    voiceLangIndex
                ].code;


            try {

                recognition.start();

                isListening = true;

                micBtn.classList.add(
                    "listening"
                );

                status.textContent =
                    "● Listening...";

            }

            catch (error) {

                console.error(
                    "Could not start voice input:",
                    error
                );

            }

        }
    );


    voiceLangBtn.addEventListener(
        "click",
        function () {

            voiceLangIndex =
                (
                    voiceLangIndex + 1
                ) %
                voiceLanguages.length;


            voiceLangBtn.textContent =
                voiceLanguages[
                    voiceLangIndex
                ].label;

        }
    );

}


// =========================
// INITIAL LOAD
// =========================

loadPDFs();
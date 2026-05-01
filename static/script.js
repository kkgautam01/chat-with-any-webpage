let isLoading = false;

async function saveUrl() {
    const urlInput         = document.getElementById('urlInput');
    const loader           = document.getElementById('loadingIndicator');
    const setupScreen      = document.getElementById('setup-screen');
    const chatScreen       = document.getElementById('chat-screen');
    const loadBtn          = document.getElementById('loadBtn');

    if (!urlInput) return;

    const url = urlInput.value.trim();
    if (!url) return;

    loader.style.display  = 'block';
    loadBtn.disabled      = true;

    try {
        const res  = await fetch('/save_url', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ url })
        });

        const data = await res.json();

        if (!res.ok) {
            // Server returned an error (4xx / 5xx)
            loader.style.display = 'none';
            loadBtn.disabled     = false;
            showSetupError(data.error || 'Failed to load URL. Please try again.');
            return;
        }

        // Success — switch screens
        loader.style.display      = 'none';
        setupScreen.style.display = 'none';
        chatScreen.style.display  = 'flex';

        addMessage('Content loaded! Ask any question about the page. '+ url, 'bot-message', false);

    } catch (err) {
        console.error('Error saving URL:', err);
        loader.style.display = 'none';
        loadBtn.disabled     = false;
        showSetupError('Network error. Is the server running?');
    }
}

function showSetupError(msg) {
    let errEl = document.getElementById('setupError');
    if (!errEl) {
        errEl = document.createElement('p');
        errEl.id = 'setupError';
        errEl.style.cssText = 'color:#c0392b;font-size:13px;margin:0;';
        document.getElementById('setup-screen').appendChild(errEl);
    }
    errEl.textContent = msg;
}

// Returns { li, div } so callers can update the element later
function addMessage(text, type, isThinking = true) {
    const messages = document.getElementById('messages');
    if (!messages) return {};

    const li  = document.createElement('li');
    li.className = `message ${type}`;
    if (isThinking) li.classList.add('thinking');

    const div = document.createElement('div');
    div.style.whiteSpace = 'pre-wrap';
    div.innerText = text;

    li.appendChild(div);
    messages.appendChild(li);
    messages.scrollTop = messages.scrollHeight;

    return { li, div };
}

async function askQuestion() {
    const input = document.getElementById('question');
    const btn   = document.getElementById('sendBtn');
    if (!input || !btn) return;

    const question = input.value.trim();
    if (!question || isLoading) return;

    // Show user bubble
    const { li: userLi } = addMessage(question, 'user-message', true);
    input.value = '';

    // Lock UI
    isLoading     = true;
    input.disabled = true;
    btn.disabled   = true;

    // Show bot "thinking" spinner
    const { li: botLi, div: botDiv } = addMessage('', 'bot-message', false);
    botDiv.innerHTML = '<span class="spinner"></span>';

    try {
        const res  = await fetch('/ask', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ question })
        });

        const data = await res.json();

        userLi.classList.remove('thinking');
        botLi.classList.remove('loading');

        const answer = data.response || (data.error ? `Error: ${data.error}` : 'No response received.');
        let newText = cleanText(answer);
        typeText(botDiv, newText);

    } catch (err) {
        console.error('Error getting response:', err);
        userLi.classList.remove('thinking');
        botLi.classList.remove('loading');
        botDiv.innerText = "Network error. Please check your connection and try again.";
    }

    isLoading      = false;
    input.disabled = false;
    btn.disabled   = false;
    input.focus();
}

// Enter-key support
document.getElementById('question')?.addEventListener('keydown', e => {
    if (e.key === 'Enter') askQuestion();
});

// Smooth typing effect
function typeText(element, text, speed = 1) {
    let i = 0;
    let raw = "";
    const messages = document.getElementById('messages');
    element.innerHTML = marked.parse(cleanText(text));
    messages.scrollTop = messages.scrollHeight;
    // element.innerText = '';
    //
    // (function typing() {
    //     if (i < text.length) {
    //         raw += text.charAt(i++);
    //         element.innerText = raw;
    //
    //         messages.scrollTop = messages.scrollHeight;
    //         setTimeout(typing, speed);
    //     } else {
    //         element.innerHTML = marked.parse(raw);
    //     }
    // })();
}

function cleanText(text) {
    return text
        .replace(/\n{3,}/g, "\n\n")   // max 2 line breaks
        .replace(/\n\s*\n/g, "\n\n")  // normalize empty lines
        .trim();
}

// function typeText(element, text, speed = 15) {
//     let i = 0;
//     element.innerText = '';
//     const messages = document.getElementById('messages');
//
//     (function typing() {
//         if (i < text.length) {
//             element.innerText += text.charAt(i++);
//             messages.scrollTop  = messages.scrollHeight;
//             setTimeout(typing, speed);
//         }
//     })();
// }
async function sendMessage(userMessage = null) {
    const answerBox = document.getElementById("talk-message");

    if (!userMessage) {
        userMessage = prompt("바질이에게 뭐라고 말할까요?");
    }

    if (!userMessage) return;

    answerBox.innerText = "나: " + userMessage + "\n바질이가 생각 중이에요... 🌱";

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: userMessage
            })
        });

        const data = await response.json();

        console.log("서버 응답:", data);
        console.log("TTS 실행됨:", data.answer);


        answerBox.innerText = "나: " + userMessage + "\n바질이: " + data.answer;

        speakText(data.answer);

    } catch (error) {
        answerBox.innerText = "오류가 났어요. 터미널을 확인해주세요.";
        console.error(error);
    }
}

function startVoiceInput() {
    const answerBox = document.getElementById("talk-message");

    const SpeechRecognition =
        window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        answerBox.innerText = "이 브라우저는 음성 인식을 지원하지 않아요. 크롬에서 실행해주세요.";
        return;
    }

    const recognition = new SpeechRecognition();

    recognition.lang = "ko-KR";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    answerBox.innerText = "듣고 있어요... 🎤";

    recognition.start();

    recognition.onresult = function (event) {
        const voiceText = event.results[0][0].transcript;
        answerBox.innerText = "들은 말: " + voiceText;

        sendMessage(voiceText);
    };

    recognition.onerror = function (event) {
        answerBox.innerText = "음성 인식 중 오류가 났어요: " + event.error;
    };

    recognition.onend = function () {
        console.log("음성 인식 종료");
    };
}

function speakText(text) {
    if (!window.speechSynthesis) {
        console.log("이 브라우저는 음성 출력을 지원하지 않아요.");
        return;
    }

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "ko-KR";
    utterance.rate = 1.0;
    utterance.pitch = 1.2;

    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
}
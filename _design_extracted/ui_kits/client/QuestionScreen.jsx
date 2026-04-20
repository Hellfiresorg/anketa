// Question/answer screen with mic button + textarea
const { useState } = React;

function QuestionScreen({ question, currentIdx = 0, total = 10, initialText = '', onNext }) {
  const [text, setText] = useState(initialText);
  const [isListening, setIsListening] = useState(false);

  const toggleMic = () => {
    // Fake the recording animation — real app uses SpeechRecognition API
    setIsListening((v) => !v);
    if (!isListening) {
      setTimeout(() => {
        setText((prev) =>
          prev
            ? prev + ' Хочу получить консультацию по услугам.'
            : 'Хочу получить консультацию по услугам.'
        );
        setIsListening(false);
      }, 1800);
    }
  };

  const q = question || {
    order_index: 1,
    text: 'С какой целью вы обращаетесь?',
    hint: 'Опишите вкратце в одном-двух предложениях',
    is_required: true,
  };

  return (
    <div className="client-screen" style={{ paddingTop: 24 }}>
      <ProgressBar current={currentIdx + 1} total={total} />
      <div className="client-qa">
        <p className="client-caption">Вопрос {q.order_index} из {total}</p>
        <h2 className="client-h2">{q.text}</h2>
        {q.hint && <p className="client-hint">{q.hint}</p>}

        <div className="client-textarea-wrap">
          <textarea
            className="client-textarea"
            placeholder="Введите ответ или нажмите кнопку микрофона для голосового ввода"
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <button
            onClick={toggleMic}
            className={`client-mic-btn ${isListening ? 'rec' : ''}`}
            title={isListening ? 'Остановить' : 'Голосовой ввод'}
            aria-label={isListening ? 'Остановить запись' : 'Голосовой ввод'}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
              <rect x="9" y="2" width="6" height="11" rx="3"/>
              <path d="M5 10a7 7 0 0 0 14 0"/>
              <line x1="12" y1="17" x2="12" y2="22"/>
              <line x1="8" y1="22" x2="16" y2="22"/>
            </svg>
          </button>
        </div>

        {isListening && <p className="client-listening">Слушаю...</p>}

        <button
          onClick={() => onNext && onNext(text)}
          disabled={q.is_required && !text.trim()}
          className="client-btn-primary"
          style={{ marginTop: 24, width: '100%' }}
        >
          {currentIdx + 1 < total ? 'Далее →' : 'К проверке'}
        </button>
      </div>
    </div>
  );
}
window.QuestionScreen = QuestionScreen;

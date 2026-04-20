// Welcome screen: logo, greeting, question count, start button
function WelcomeScreen({ clientName = 'Иван', totalQuestions = 10, onStart }) {
  return (
    <div className="client-screen" style={{ textAlign: 'center', justifyContent: 'center' }}>
      <div className="client-logo">
        <div className="client-logo-mark">А</div>
      </div>
      <h1 className="client-h1">Добро пожаловать, {clientName}!</h1>
      <p className="client-body">
        Вам предстоит ответить на <strong>{totalQuestions}</strong> вопросов.
      </p>
      <p className="client-caption" style={{ marginBottom: 32 }}>
        Примерное время: {Math.ceil(totalQuestions * 1.5)} минут
      </p>
      <button className="client-btn-primary client-btn-lg" onClick={onStart}>
        Начать
      </button>
    </div>
  );
}

window.WelcomeScreen = WelcomeScreen;

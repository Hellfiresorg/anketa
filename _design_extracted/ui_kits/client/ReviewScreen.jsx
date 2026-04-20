// Review screen: list of Q/A with click-to-edit
function ReviewScreen({ questions = [], answers = {}, onEdit, onSubmit, submitError }) {
  return (
    <div className="client-screen" style={{ paddingTop: 32 }}>
      <div className="client-review">
        <h2 className="client-h2-brand">Проверьте ответы</h2>
        <p className="client-body-muted">Нажмите на вопрос, чтобы отредактировать ответ.</p>
        {submitError && <p style={{ color: '#ef4444', fontSize: 14, marginTop: 16 }}>{submitError}</p>}

        <div className="client-review-list">
          {questions.map((q, idx) => (
            <div key={q.id} className="client-review-item" onClick={() => onEdit && onEdit(idx)}>
              <p className="client-review-q">{q.order_index}. {q.text}</p>
              <p className="client-review-a">
                {answers[q.id] || <span style={{ color: '#d97706' }}>Нет ответа</span>}
              </p>
            </div>
          ))}
        </div>

        <button onClick={onSubmit} className="client-btn-primary" style={{ marginTop: 32, width: '100%' }}>
          Отправить анкету
        </button>
      </div>
    </div>
  );
}
window.ReviewScreen = ReviewScreen;

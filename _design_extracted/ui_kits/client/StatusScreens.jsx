function ThankYouScreen() {
  return (
    <div className="client-screen" style={{ justifyContent: 'center', textAlign: 'center' }}>
      <div style={{ width: 72, height: 72, borderRadius: '9999px', background: '#dcfce7', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 24, marginLeft: 'auto', marginRight: 'auto' }}>
        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#16a34a" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
      </div>
      <h2 className="client-h2-brand">Спасибо!</h2>
      <p className="client-body-muted" style={{ maxWidth: 360 }}>
        Ваша анкета успешно отправлена. Мы свяжемся с вами в ближайшее время.
      </p>
    </div>
  );
}

function SubmittingScreen() {
  return (
    <div className="client-screen" style={{ justifyContent: 'center', textAlign: 'center' }}>
      <p className="client-body-muted pulse">Отправляем анкету...</p>
    </div>
  );
}

function ReadonlyScreen({ questions = [], answers = {} }) {
  return (
    <div className="client-screen" style={{ paddingTop: 32 }}>
      <div className="client-review">
        <div className="client-banner-amber">
          <p className="client-banner-title">Анкета уже заполнена</p>
          <p className="client-banner-sub">Редактирование недоступно. Ниже — ваши ответы.</p>
        </div>
        <h2 className="client-h2-brand" style={{ marginTop: 24 }}>Ваши ответы</h2>
        <div className="client-review-list" style={{ marginTop: 24 }}>
          {questions.map((q) => (
            <div key={q.id} className="client-review-item" style={{ cursor: 'default' }}>
              <p className="client-review-q">{q.order_index}. {q.text}</p>
              {answers[q.id]
                ? <p className="client-review-a">{answers[q.id]}</p>
                : <p style={{ fontSize: 14, color: '#9ca3af' }}>Нет ответа</p>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

window.ThankYouScreen = ThankYouScreen;
window.SubmittingScreen = SubmittingScreen;
window.ReadonlyScreen = ReadonlyScreen;

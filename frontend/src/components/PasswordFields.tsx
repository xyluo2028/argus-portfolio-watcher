/** A new password typed twice, as the server wants it (at least 8 characters). */
const MIN_PASSWORD = 8;

export function NewPasswordFields({ password, confirm, onPassword, onConfirm, label = "Password" }: {
  password: string; confirm: string; onPassword: (v: string) => void; onConfirm: (v: string) => void; label?: string;
}) {
  const mismatch = confirm !== "" && confirm !== password;
  return (
    <>
      <label className="field">{label}
        <input className="input" type="password" autoComplete="new-password" value={password}
               onChange={(e) => onPassword(e.target.value)} />
        <span className="small muted">At least {MIN_PASSWORD} characters.</span>
      </label>
      <label className="field">Repeat it
        <input className="input" type="password" autoComplete="new-password" value={confirm}
               onChange={(e) => onConfirm(e.target.value)} aria-invalid={mismatch} />
        {mismatch && <span className="small" style={{ color: "var(--down)" }}>Doesn't match.</span>}
      </label>
    </>
  );
}

export const passwordReady = (password: string, confirm: string) => password.length >= MIN_PASSWORD && password === confirm;

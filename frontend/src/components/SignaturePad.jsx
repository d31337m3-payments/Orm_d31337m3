import React, { useRef, useState, useEffect } from "react";
import { Eraser, Save } from "lucide-react";

export default function SignaturePad({ onSave, fullName, setFullName, existing }) {
  const canvasRef = useRef(null);
  const [drawing, setDrawing] = useState(false);
  const [hasSig, setHasSig] = useState(false);

  useEffect(() => {
    const c = canvasRef.current;
    if (!c) return;
    const ctx = c.getContext("2d");
    ctx.fillStyle = "#0a0a0a";
    ctx.fillRect(0, 0, c.width, c.height);
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 2.5;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
  }, []);

  const getPos = (e) => {
    const c = canvasRef.current;
    const rect = c.getBoundingClientRect();
    const sx = c.width / rect.width;
    const sy = c.height / rect.height;
    const t = e.touches ? e.touches[0] : e;
    return { x: (t.clientX - rect.left) * sx, y: (t.clientY - rect.top) * sy };
  };

  const start = (e) => {
    e.preventDefault();
    setDrawing(true);
    const { x, y } = getPos(e);
    const ctx = canvasRef.current.getContext("2d");
    ctx.beginPath();
    ctx.moveTo(x, y);
  };
  const draw = (e) => {
    if (!drawing) return;
    e.preventDefault();
    const { x, y } = getPos(e);
    const ctx = canvasRef.current.getContext("2d");
    ctx.lineTo(x, y);
    ctx.stroke();
    setHasSig(true);
  };
  const stop = () => setDrawing(false);

  const clear = () => {
    const c = canvasRef.current;
    const ctx = c.getContext("2d");
    ctx.fillStyle = "#0a0a0a";
    ctx.fillRect(0, 0, c.width, c.height);
    setHasSig(false);
  };

  const save = () => {
    if (!fullName || !fullName.trim()) {
      alert("Please type your full legal name first.");
      return;
    }
    if (!hasSig) {
      alert("Please draw your signature on the canvas.");
      return;
    }
    const dataUrl = canvasRef.current.toDataURL("image/png");
    onSave(dataUrl);
  };

  return (
    <div className="brutal-card p-6" data-testid="signature-pad">
      <div className="overline mb-3">// e-signature consent</div>
      <p className="font-mono text-xs text-zinc-400 mb-4 leading-relaxed">
        By typing your full legal name and signing below, you authorize d31337m3 to apply this
        signature to legal documents (DMCA notices, cease &amp; desist letters, privacy removal
        requests) generated and sent on your behalf. This is legally binding under the
        U.S. ESIGN Act, Canada&apos;s PIPEDA &amp; UECA, and Mexico&apos;s LFFEA.
      </p>

      <div className="overline mb-1">full legal name</div>
      <input
        data-testid="signature-name-input"
        value={fullName}
        onChange={(e) => setFullName(e.target.value)}
        placeholder="e.g. John A. Doe"
        className="brutal-input mb-4"
      />

      {existing && (
        <div className="mb-4 border border-[#222] p-3 bg-[#0a0a0a]">
          <div className="overline mb-2">// current signature on file</div>
          <img src={existing.data_url} alt="signature" className="max-h-24 bg-white p-2 inline-block" />
          <div className="font-mono text-xs text-zinc-500 mt-2">› {existing.full_name} · {existing.created_at?.slice(0, 16)}</div>
        </div>
      )}

      <div className="overline mb-1">sign below</div>
      <canvas
        ref={canvasRef}
        width={700}
        height={200}
        data-testid="signature-canvas"
        onMouseDown={start} onMouseMove={draw} onMouseUp={stop} onMouseLeave={stop}
        onTouchStart={start} onTouchMove={draw} onTouchEnd={stop}
        className="w-full border border-[#222] cursor-crosshair touch-none"
        style={{ background: "#0a0a0a" }}
      />
      <div className="flex gap-3 mt-4">
        <button onClick={clear} data-testid="signature-clear" className="brutal-btn flex items-center gap-2"><Eraser size={14}/>Clear</button>
        <button onClick={save} data-testid="signature-save" className="brutal-btn brutal-btn-primary flex items-center gap-2"><Save size={14}/>Save Signature</button>
      </div>
    </div>
  );
}

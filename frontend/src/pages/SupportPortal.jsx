import React, { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { useNavigate, Link } from "react-router-dom";
import { MessageSquare, Ticket, ShieldAlert, Send } from "lucide-react";
import api from "@/lib/api";

export default function SupportPortal() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const [tab, setTab] = useState("chats");
  const [chats, setChats] = useState([]);
  const [tickets, setTickets] = useState([]);
  const [selectedChat, setSelectedChat] = useState(null);
  const [messages, setMessages] = useState([]);
  const [replyText, setReplyText] = useState("");
  const [screenName, setScreenName] = useState("");

  useEffect(() => {
    if (loading) return;
    if (!user) { navigate("/login"); return; }
  }, [user, loading, navigate]);

  useEffect(() => {
    if (!user) return;
    api.get("/api/support/admin/chats").then(r => setChats(r.data?.chats || [])).catch(() => {});
    api.get("/api/support/admin/tickets").then(r => setTickets(r.data?.tickets || [])).catch(() => {});
  }, [user]);

  useEffect(() => {
    if (!selectedChat) return;
    api.get(`/api/support/admin/chats/${selectedChat}/messages`).then(r => setMessages(r.data?.messages || [])).catch(() => {});
  }, [selectedChat]);

  const sendReply = async () => {
    if (!replyText.trim() || !selectedChat) return;
    try {
      await api.post(`/api/support/admin/chats/${selectedChat}/messages`, { text: replyText });
      setReplyText("");
      const r = await api.get(`/api/support/admin/chats/${selectedChat}/messages`);
      setMessages(r.data?.messages || []);
    } catch {}
  };

  if (loading) return <div className="min-h-screen bg-[#050505] flex items-center justify-center"><div className="font-mono text-zinc-500">loading...</div></div>;
  if (!user) return null;

  const isStaff = !!user.employee_number;

  return (
    <div className="min-h-screen bg-[#050505] text-white">
      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <Link to="/" className="font-mono text-xs text-zinc-500 hover:text-white">← home</Link>
            <h1 className="font-display font-black text-3xl mt-1">Support Portal</h1>
          </div>
          <div className="flex items-center gap-3">
            <span className="font-mono text-xs text-zinc-500">{user.email}</span>
            {isStaff && <span className="text-xs text-[#00FF41] font-mono border border-[#00FF41]/30 px-2 py-0.5">EMP {user.employee_number}</span>}
          </div>
        </div>

        {!isStaff && (
          <div className="brutal-card p-8 border border-[#FF3333]/50 text-center">
            <ShieldAlert size={32} className="text-[#FF3333] mx-auto mb-3" />
            <h2 className="font-display font-black text-xl mb-2">Access Restricted</h2>
            <p className="font-mono text-sm text-zinc-400">
              This portal requires an active employee account with a valid employee number.
              Contact your administrator if you believe this is an error.
            </p>
          </div>
        )}

        {isStaff && (
          <>
            <div className="flex gap-2 mb-6 flex-wrap">
              {[
                ["chats", "Live Chats", MessageSquare],
                ["tickets", "Tickets", Ticket],
              ].map(([k, l, Icon]) => (
                <button key={k} onClick={() => setTab(k)}
                  className={`font-mono text-xs px-4 py-2 border flex items-center gap-2 ${
                    tab === k ? "border-white text-white" : "border-[#222] text-zinc-500 hover:text-white"
                  }`}>
                  <Icon size={14} /> {l}
                </button>
              ))}
            </div>

            {tab === "chats" && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-1 brutal-card p-4">
                  <h2 className="font-display font-black text-lg mb-3">Chat Queue</h2>
                  {chats.filter(c => c.status !== "closed").map(c => (
                    <button key={c.id} onClick={() => setSelectedChat(c.id)}
                      className={`w-full text-left font-mono text-xs border p-2 mb-2 transition-colors ${
                        selectedChat === c.id ? "border-[#00FF41] bg-[#00FF41]/5" : "border-[#222] hover:border-zinc-500"
                      }`}>
                      <div className="text-white">{c.customer_email || "Anonymous"}</div>
                      <div className="text-zinc-500 mt-1">{c.message_count || 0} messages</div>
                      <span className={`text-xs ${c.status === "waiting" ? "text-[#FFD700]" : "text-[#00FF41]"}`}>{c.status}</span>
                    </button>
                  ))}
                  {chats.filter(c => c.status !== "closed").length === 0 && (
                    <p className="font-mono text-xs text-zinc-600">No active chats.</p>
                  )}
                </div>
                <div className="lg:col-span-2 brutal-card p-4 flex flex-col">
                  {selectedChat ? (
                    <>
                      <div className="flex items-center justify-between mb-3">
                        <h2 className="font-display font-black text-lg">Chat</h2>
                        <div className="flex items-center gap-2">
                          <input className="brutal-input !py-1 !px-2 text-xs w-40" placeholder="screen name" value={screenName} onChange={e => setScreenName(e.target.value)} />
                        </div>
                      </div>
                      <div className="flex-1 max-h-[500px] overflow-y-auto space-y-2 mb-3 bg-black/30 p-3 rounded">
                        {messages.map((m, i) => (
                          <div key={i} className={`font-mono text-xs ${m.role === "admin" || m.role === "agent" ? "text-right" : ""}`}>
                            <span className={`inline-block px-3 py-1.5 rounded max-w-[80%] ${m.role === "admin" || m.role === "agent" ? "bg-[#00FF41]/10 text-[#00FF41]" : "bg-zinc-800 text-zinc-300"}`}>
                              <div className="font-bold mb-0.5">{m.sender_name || m.role || "user"}</div>
                              {m.text}
                              {m.media_url && <div className="mt-1 text-zinc-500 underline"><a href={m.media_url} target="_blank">📎 attachment</a></div>}
                            </span>
                          </div>
                        ))}
                        {messages.length === 0 && <div className="text-zinc-600 text-center py-4">No messages yet.</div>}
                      </div>
                      <div className="flex gap-2">
                        <input className="brutal-input flex-1" placeholder="Type a reply..." value={replyText} onChange={e => setReplyText(e.target.value)} onKeyDown={e => e.key === "Enter" && sendReply()} />
                        <button onClick={sendReply} className="brutal-btn flex items-center gap-1"><Send size={14} /> Send</button>
                      </div>
                    </>
                  ) : (
                    <div className="flex items-center justify-center h-full text-zinc-600 font-mono text-sm">Select a chat from the queue</div>
                  )}
                </div>
              </div>
            )}

            {tab === "tickets" && (
              <div className="brutal-card p-6">
                <h2 className="font-display font-black text-xl mb-4">Support Tickets</h2>
                {tickets.length === 0 && <p className="font-mono text-sm text-zinc-600">No tickets yet.</p>}
                <div className="space-y-2">
                  {tickets.map(t => (
                    <div key={t.id} className="flex items-center justify-between font-mono text-xs border border-[#222] p-3">
                      <div>
                        <span className="text-white">{t.subject || "No subject"}</span>
                        <span className="text-zinc-500 ml-3">{t.customer_email || ""}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className={`px-2 py-0.5 ${t.status === "open" ? "text-[#00FF41]" : t.status === "closed" ? "text-zinc-500" : "text-[#FFD700]"}`}>
                          {t.status || "open"}
                        </span>
                        <span className="text-zinc-600">{t.priority || "normal"}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

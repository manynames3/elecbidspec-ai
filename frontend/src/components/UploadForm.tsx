"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Lock, Upload } from "lucide-react";
import { apiFetch } from "@/lib/api";
import type { AccountStatus, Opportunity } from "@/lib/types";

export function UploadForm() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [form, setForm] = useState({
    title: "",
    agency: "",
    location: "",
    state: "",
    due_date: "",
    naics_code: "",
    estimated_value: "",
    source_url: ""
  });
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [accountStatus, setAccountStatus] = useState<AccountStatus | null>(null);

  useEffect(() => {
    async function loadAccountStatus() {
      try {
        setAccountStatus(await apiFetch<AccountStatus>("/account/status"));
      } catch {
        setAccountStatus(null);
      }
    }
    void loadAccountStatus();
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!accountStatus?.authenticated) {
      setError("Pilot login required to upload RFP/spec documents.");
      return;
    }
    if (!file) {
      setError("Choose a PDF or text file first.");
      return;
    }
    setSaving(true);
    setError(null);
    const body = new FormData();
    body.append("file", file);
    Object.entries(form).forEach(([key, value]) => {
      if (value) {
        body.append(key, value);
      }
    });
    try {
      const opportunity = await apiFetch<Opportunity>("/uploads", { method: "POST", body });
      router.push(`/opportunities?id=${opportunity.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="page-stack">
      <section className="page-header">
        <div>
          <p className="eyebrow">Manual bid intake</p>
          <h1>Upload RFP or spec documents</h1>
        </div>
      </section>

      {!accountStatus?.authenticated ? (
        <div className="pilot-gate-banner">
          <Lock size={17} />
          <span>Sign in to a pilot workspace before uploading RFP/spec documents.</span>
        </div>
      ) : null}

      <form className="form-panel" onSubmit={submit}>
        <label className="file-drop">
          <Upload size={24} />
          <span>{file ? file.name : "Choose PDF or text attachment"}</span>
          <input
            type="file"
            accept=".pdf,.txt,.md"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
        </label>

        <div className="form-grid">
          <label>
            <span>Title</span>
            <input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} placeholder="RFP title" />
          </label>
          <label>
            <span>Agency</span>
            <input value={form.agency} onChange={(event) => setForm({ ...form, agency: event.target.value })} placeholder="Issuing agency" />
          </label>
          <label>
            <span>Location</span>
            <input value={form.location} onChange={(event) => setForm({ ...form, location: event.target.value })} placeholder="City, ST" />
          </label>
          <label>
            <span>State</span>
            <input maxLength={2} value={form.state} onChange={(event) => setForm({ ...form, state: event.target.value.toUpperCase() })} placeholder="TX" />
          </label>
          <label>
            <span>Due date</span>
            <input type="date" value={form.due_date} onChange={(event) => setForm({ ...form, due_date: event.target.value })} />
          </label>
          <label>
            <span>NAICS code</span>
            <input value={form.naics_code} onChange={(event) => setForm({ ...form, naics_code: event.target.value })} placeholder="237130" />
          </label>
          <label>
            <span>Estimated value</span>
            <input type="number" min="0" value={form.estimated_value} onChange={(event) => setForm({ ...form, estimated_value: event.target.value })} placeholder="5000000" />
          </label>
          <label>
            <span>Source URL</span>
            <input value={form.source_url} onChange={(event) => setForm({ ...form, source_url: event.target.value })} placeholder="https://..." />
          </label>
        </div>

        {error ? <div className="alert">{error}</div> : null}
        <button className="primary-button" type="submit" disabled={saving || !accountStatus?.authenticated}>
          <Upload size={17} />
          {saving ? "Processing..." : "Extract specs"}
        </button>
      </form>
    </div>
  );
}

"use client";

import { FormEvent, useEffect, useState } from "react";
import { Save } from "lucide-react";
import { apiFetch } from "@/lib/api";
import type { CompanyProfile } from "@/lib/types";

const experienceKeys = [
  "data_center_power",
  "utility_replacement",
  "fire_damage_rebuild",
  "underground_installation",
  "pole_overhead_installation",
  "substation_related"
];

function splitList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function ProfileForm() {
  const [profileId, setProfileId] = useState<number | null>(null);
  const [form, setForm] = useState({
    name: "",
    states_served: "",
    bonding_capacity: "",
    cable_types_supplied: "",
    installation_capabilities: "",
    labor_type: "union",
    experience: Object.fromEntries(experienceKeys.map((key) => [key, false])) as Record<string, boolean>
  });
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const profile = await apiFetch<CompanyProfile>("/company-profile");
        setProfileId(profile.id);
        setForm({
          name: profile.name,
          states_served: profile.states_served.join(", "),
          bonding_capacity: profile.bonding_capacity ? String(profile.bonding_capacity) : "",
          cable_types_supplied: profile.cable_types_supplied.join(", "),
          installation_capabilities: profile.installation_capabilities.join(", "),
          labor_type: profile.labor_type ?? "",
          experience: { ...form.experience, ...profile.experience }
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load profile");
      }
    }
    void load();
  }, []);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus(null);
    setError(null);
    try {
      const payload = {
        name: form.name,
        states_served: splitList(form.states_served).map((state) => state.toUpperCase()),
        bonding_capacity: form.bonding_capacity ? Number(form.bonding_capacity) : null,
        cable_types_supplied: splitList(form.cable_types_supplied),
        installation_capabilities: splitList(form.installation_capabilities),
        labor_type: form.labor_type,
        experience: form.experience
      };
      const saved = await apiFetch<CompanyProfile>("/company-profile", {
        method: "PUT",
        body: JSON.stringify(payload)
      });
      setProfileId(saved.id);
      setStatus("Profile saved and opportunity fit scores refreshed.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save profile");
    }
  }

  return (
    <div className="page-stack">
      <section className="page-header">
        <div>
          <p className="eyebrow">Fit scoring inputs</p>
          <h1>Company capability profile</h1>
        </div>
        {profileId ? <span className="source-pill">profile #{profileId}</span> : null}
      </section>

      <form className="form-panel" onSubmit={save}>
        <div className="form-grid">
          <label>
            <span>Company name</span>
            <input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
          </label>
          <label>
            <span>States served</span>
            <input value={form.states_served} onChange={(event) => setForm({ ...form, states_served: event.target.value })} placeholder="CA, NV, TX" />
          </label>
          <label>
            <span>Bonding capacity</span>
            <input type="number" min="0" value={form.bonding_capacity} onChange={(event) => setForm({ ...form, bonding_capacity: event.target.value })} />
          </label>
          <label>
            <span>Labor type</span>
            <select value={form.labor_type} onChange={(event) => setForm({ ...form, labor_type: event.target.value })}>
              <option value="union">Union</option>
              <option value="non-union">Non-union</option>
              <option value="mixed">Mixed</option>
            </select>
          </label>
          <label className="wide-control">
            <span>Cable types supplied</span>
            <input value={form.cable_types_supplied} onChange={(event) => setForm({ ...form, cable_types_supplied: event.target.value })} placeholder="medium_voltage, high_voltage, conduit, fiber" />
          </label>
          <label className="wide-control">
            <span>Installation capabilities</span>
            <input value={form.installation_capabilities} onChange={(event) => setForm({ ...form, installation_capabilities: event.target.value })} placeholder="underground, overhead, pole_line, substation" />
          </label>
        </div>

        <section className="panel embedded-panel">
          <h2>Experience</h2>
          <div className="checkbox-grid">
            {experienceKeys.map((key) => (
              <label key={key} className="checkbox-label">
                <input
                  type="checkbox"
                  checked={form.experience[key] ?? false}
                  onChange={(event) =>
                    setForm({
                      ...form,
                      experience: { ...form.experience, [key]: event.target.checked }
                    })
                  }
                />
                <span>{key.replaceAll("_", " ")}</span>
              </label>
            ))}
          </div>
        </section>

        {error ? <div className="alert">{error}</div> : null}
        {status ? <div className="success">{status}</div> : null}
        <button className="primary-button" type="submit">
          <Save size={17} />
          Save profile
        </button>
      </form>
    </div>
  );
}


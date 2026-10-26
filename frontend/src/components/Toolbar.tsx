import { Filter, Search, UserRound } from "lucide-react";
import type { RecruiterOption } from "../recruiters";
import { Field, controlClasses } from "./Field";

interface ToolbarProps {
  recruiters: RecruiterOption[];
  recruiterId: string;
  onRecruiterChange: (id: string) => void;
  search: string;
  onSearchChange: (value: string) => void;
  statuses: string[];
  status: string;
  onStatusChange: (value: string) => void;
}

export function Toolbar(props: ToolbarProps) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
      <Field label="Recruiter" icon={<UserRound aria-hidden="true" className="size-3.5" />}>
        <select
          className={controlClasses}
          value={props.recruiterId}
          onChange={(e) => props.onRecruiterChange(e.target.value)}
        >
          {props.recruiters.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name}
            </option>
          ))}
        </select>
      </Field>

      <Field label="Search" icon={<Search aria-hidden="true" className="size-3.5" />}>
        <input
          type="text"
          className={controlClasses}
          value={props.search}
          onChange={(e) => props.onSearchChange(e.target.value)}
          placeholder="Name, email, role..."
        />
      </Field>

      <Field label="Status" icon={<Filter aria-hidden="true" className="size-3.5" />}>
        <select
          className={`${controlClasses} capitalize`}
          value={props.status}
          onChange={(e) => props.onStatusChange(e.target.value)}
        >
          <option value="">All</option>
          {props.statuses.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </Field>
    </div>
  );
}

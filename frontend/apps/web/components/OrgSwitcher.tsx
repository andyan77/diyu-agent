"use client";

/**
 * Organization switcher component.
 *
 * Task card: FW1-3
 * - Switch organization -> API header org_id changes -> data refreshes
 * - Displays current org name
 * - Dropdown with available orgs
 *
 * Dependencies: OrgContext (G1-2)
 */

import { useCallback, useState, type ReactNode } from "react";

// --- Types ---

export interface Organization {
  id: string;
  name: string;
}

interface OrgSwitcherProps {
  /** Currently selected organization */
  current: Organization;
  /** Available organizations for the user */
  organizations: Organization[];
  /** Callback when user switches organization */
  onSwitch: (org: Organization) => void;
}

/**
 * Dropdown component for switching between organizations.
 * On switch, the parent should:
 * 1. Update the org_id in API request headers
 * 2. Refresh/invalidate cached data
 * 3. Update session storage if needed
 */
export function OrgSwitcher({
  current,
  organizations,
  onSwitch,
}: OrgSwitcherProps) {
  const [isOpen, setIsOpen] = useState(false);

  const handleToggle = useCallback(() => {
    setIsOpen((prev) => !prev);
  }, []);

  const handleSelect = useCallback(
    (org: Organization) => {
      if (org.id !== current.id) {
        onSwitch(org);
      }
      setIsOpen(false);
    },
    [current.id, onSwitch],
  );

  return (
    <div data-testid="org-switcher" style={{ position: "relative" }}>
      <button
        type="button"
        onClick={handleToggle}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        data-testid="org-switcher-trigger"
      >
        {current.name}
      </button>

      {isOpen && (
        <ul
          role="listbox"
          aria-label="Select organization"
          data-testid="org-switcher-list"
          style={{
            position: "absolute",
            top: "100%",
            left: 0,
            listStyle: "none",
            padding: 0,
            margin: 0,
          }}
        >
          {organizations.map((org) => (
            <li key={org.id} role="option" aria-selected={org.id === current.id}>
              <button
                type="button"
                onClick={() => handleSelect(org)}
                data-testid={`org-option-${org.id}`}
              >
                {org.name}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

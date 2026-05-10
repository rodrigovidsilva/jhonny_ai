"use client";

import { useEffect, useRef, useState } from "react";
import { Briefcase, MapPin, PencilLine, Shield } from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { cn, getInitials } from "@/lib/utils";

export type AppUser = {
  displayName: string;
  email: string;
  role: string;
  jobTitle?: string;
  officeLocation?: string;
};

type ProfileDraft = {
  displayName: string;
  jobTitle: string;
  officeLocation: string;
};

type UserProfileMenuProps = {
  user: AppUser;
  onSaveProfile?: (draft: ProfileDraft) => void | Promise<void>;
};

function buildProfileDraft(user: AppUser): ProfileDraft {
  return {
    displayName: user.displayName || "",
    jobTitle: user.jobTitle || "",
    officeLocation: user.officeLocation || "",
  };
}

export function UserProfileMenu({ user, onSaveProfile }: UserProfileMenuProps) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [draft, setDraft] = useState<ProfileDraft>(() => buildProfileDraft(user));
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setDraft(buildProfileDraft(user));
  }, [user]);

  useEffect(() => {
    if (!isMenuOpen) return;

    const handlePointerDown = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsMenuOpen(false);
      }
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setIsMenuOpen(false);
    };

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleEscape);

    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [isMenuOpen]);

  const visibleName = user.displayName || user.email;
  const menuAvatarContent = getInitials(visibleName);
  const draftAvatarContent = getInitials(draft.displayName || user.email);

  async function saveProfile() {
    if (!onSaveProfile) {
      setIsDialogOpen(false);
      return;
    }

    setIsSaving(true);
    try {
      await onSaveProfile(draft);
      setIsDialogOpen(false);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <>
      <div ref={menuRef} className="relative ml-1 shrink-0">
        <button
          type="button"
          onClick={() => setIsMenuOpen((currentValue) => !currentValue)}
          aria-expanded={isMenuOpen}
          aria-haspopup="dialog"
          title="Open profile"
          className={cn(
            "inline-flex h-10 w-10 items-center justify-center rounded-full border border-transparent !bg-transparent !p-0 !shadow-none transition-colors hover:border-border/70 hover:!bg-background/50",
            isMenuOpen && "border-border/70 !bg-background/50 text-foreground dark:border-eyp-blue/20 dark:!bg-eyp-bg-light/80"
          )}
        >
          <Avatar className="h-8 w-8 border border-border">
            <AvatarFallback className="bg-eyp-blue/20 text-xs text-eyp-blue">
              {menuAvatarContent}
            </AvatarFallback>
          </Avatar>
          <span className="sr-only">Open profile menu</span>
        </button>

        {isMenuOpen && (
          <div className="absolute right-0 top-full z-50 mt-2 w-80 rounded-xl border border-eyp-blue/15 bg-eyp-bg-light/95 p-3 shadow-[0_20px_60px_-42px_rgba(26,154,250,0.65)] backdrop-blur">
            <div className="flex items-start gap-3">
              <Avatar className="h-11 w-11 border border-border">
                <AvatarFallback className="bg-eyp-blue/20 text-sm text-eyp-blue">
                  {menuAvatarContent}
                </AvatarFallback>
              </Avatar>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold">{visibleName}</p>
                <p className="truncate text-xs text-muted-foreground">{user.email}</p>
              </div>
            </div>

            <div className="mt-3 grid gap-1.5 text-xs text-muted-foreground">
              <div className="flex items-center gap-2">
                <Shield className="h-3.5 w-3.5" />
                <span className="truncate">{user.role}</span>
              </div>
              {user.jobTitle && (
                <div className="flex items-center gap-2">
                  <Briefcase className="h-3.5 w-3.5" />
                  <span className="truncate">{user.jobTitle}</span>
                </div>
              )}
              {user.officeLocation && (
                <div className="flex items-center gap-2">
                  <MapPin className="h-3.5 w-3.5" />
                  <span className="truncate">{user.officeLocation}</span>
                </div>
              )}
            </div>

            <Separator className="my-3" />

            <Button
              type="button"
              variant="secondary"
              size="sm"
              className="w-full justify-start gap-2"
              onClick={() => {
                setDraft(buildProfileDraft(user));
                setIsMenuOpen(false);
                setIsDialogOpen(true);
              }}
            >
              <PencilLine className="h-4 w-4" />
              Edit profile
            </Button>
          </div>
        )}
      </div>

      <Dialog
        open={isDialogOpen}
        onOpenChange={(open) => {
          setIsDialogOpen(open);
          if (open) setDraft(buildProfileDraft(user));
        }}
      >
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>Edit profile</DialogTitle>
            <DialogDescription>
              Update your profile display details. Future apps can wire this dialog to their own
              profile API with `onSaveProfile`.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-5">
            <div className="rounded-xl border border-border/70 bg-background/70 p-4">
              <div className="flex items-center gap-3">
                <Avatar className="h-12 w-12 border border-border">
                  <AvatarFallback className="bg-eyp-blue/20 text-sm text-eyp-blue">
                    {draftAvatarContent}
                  </AvatarFallback>
                </Avatar>
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold">{draft.displayName || user.email}</p>
                  <p className="truncate text-xs text-muted-foreground">{user.email}</p>
                </div>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="grid gap-2">
                <label htmlFor="profile-display-name" className="text-sm font-medium">
                  Display name
                </label>
                <Input
                  id="profile-display-name"
                  value={draft.displayName}
                  maxLength={255}
                  onChange={(event) =>
                    setDraft((currentValue) => ({
                      ...currentValue,
                      displayName: event.target.value,
                    }))
                  }
                />
              </div>

              <div className="grid gap-2">
                <label htmlFor="profile-job-title" className="text-sm font-medium">
                  Job title
                </label>
                <Input
                  id="profile-job-title"
                  value={draft.jobTitle}
                  placeholder="AI Program Manager"
                  maxLength={255}
                  onChange={(event) =>
                    setDraft((currentValue) => ({
                      ...currentValue,
                      jobTitle: event.target.value,
                    }))
                  }
                />
              </div>

              <div className="grid gap-2 sm:col-span-2">
                <label htmlFor="profile-location" className="text-sm font-medium">
                  Office location
                </label>
                <Input
                  id="profile-location"
                  value={draft.officeLocation}
                  placeholder="Dublin"
                  maxLength={255}
                  onChange={(event) =>
                    setDraft((currentValue) => ({
                      ...currentValue,
                      officeLocation: event.target.value,
                    }))
                  }
                />
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)}>
              Cancel
            </Button>
            <Button type="button" onClick={saveProfile} disabled={isSaving}>
              {isSaving ? "Saving..." : "Save profile"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

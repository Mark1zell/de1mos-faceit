import { createClient } from "supabase";

export const supabase = createClient(
  Deno.env.get("SUPABASE_URL")!,
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
);

export const STORAGE_BUCKET = "avatars";

export function buildUserResponse(user: any) {
  const played = user.matches_played || 0;
  const wins = user.wins || 0;
  return {
    telegram_id: user.telegram_id,
    username: user.username,
    display_name: user.display_name,
    photo_url: user.photo_url,
    standoff_id: user.standoff_id,
    custom_avatar: user.custom_avatar,
    elo: user.elo || 1000,
    level: user.level || 1,
    matches_played: played,
    wins,
    winrate: played > 0 ? Math.round((wins / played) * 1000) / 10 : 0,
  };
}

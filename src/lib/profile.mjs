export function normalizeProfile(value) {
  if (typeof value !== 'string') throw new Error('Informe um perfil do Instagram.');
  let profile = value.trim();
  if (/^https?:\/\//i.test(profile)) {
    const url = new URL(profile);
    if (!['instagram.com','www.instagram.com'].includes(url.hostname) || url.port || url.username || url.password) throw new Error('Use um link de perfil do Instagram.');
    const parts = url.pathname.split('/').filter(Boolean);
    if (parts.length !== 1) throw new Error('Informe o perfil, não o link de uma publicação.');
    profile = parts[0];
  }
  profile = profile.replace(/^@/, '').toLowerCase();
  if (!/^[a-z0-9_][a-z0-9_.]{0,29}$/.test(profile) || ['p','reel','reels','explore','accounts','stories'].includes(profile)) throw new Error('Informe um nome de perfil válido.');
  return profile;
}

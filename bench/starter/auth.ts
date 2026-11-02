// Auth.js v5 config (credentials). Session carries user id + role.
import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [Credentials({ credentials: { email: {}, password: {} }, authorize: async () => null })],
  callbacks: { session: ({ session, token }) => ({ ...session, user: { ...session.user, id: token.sub, role: token.role } }) },
});

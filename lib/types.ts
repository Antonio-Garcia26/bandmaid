export type PostCategory = "general" | "music" | "live" | "fan-art";

export type FanUser = {
  uid: string;
  displayName: string;
  email: string;
};

export type Post = {
  id: string;
  title: string;
  body: string;
  category: PostCategory;
  author: Pick<FanUser, "uid" | "displayName">;
  createdAt: string;
  likes: number;
  pending?: boolean;
};

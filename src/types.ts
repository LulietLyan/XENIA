export interface Link {
  title: string;
  url: string;
  target?: string;
}

export interface Image {
  width?: string | number;
  height?: string | number;
  src: string;
  alt: string;
}

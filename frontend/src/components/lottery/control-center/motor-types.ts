export type TableKind = "table1" | "table2";

export type MotorTableRow = {
  number: number;
  formula?: string;
  visible_value?: string;
  digits_without_point?: string;
  digit_count?: number;
  code?: number;
  group_numbers?: number[];
  group_label?: string;
  literal_digit_sum?: number;
  read_only?: boolean;
  engine_ref?: string;
  table?: string;
};

export type GroupEntry = { code: number; numbers: number[]; table: string };

export type LotOption = { id: string; name: string; slug?: string };

export type MatchRow = {
  companion?: number;
  neighbor?: number;
  lottery_name?: string;
  lottery_id?: string;
  draw_date?: string;
  draw_id?: string;
  draw_time?: string;
  position?: number | string;
  position_label?: string;
  points?: number;
  score_delta?: number;
  table2_code?: number;
  table2_group?: number[];
  neighbors?: number[];
  observed_number?: number;
  mother_code?: number;
  dedupe_key?: string;
  source_reference?: string;
  draw_numbers?: unknown[];
  analyzed_at?: string;
  trace?: string;
};

export type RankRow = {
  number: number;
  table1_code?: number;
  table2_code?: number;
  table2_group?: number[];
  neighbors?: number[];
  matched_neighbors?: number[];
  score?: number;
  matches?: MatchRow[];
  trace?: string;
};

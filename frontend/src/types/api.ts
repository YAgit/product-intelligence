export type DrugMatch = {
  brand_name: string;
  generic_name: string;
  labeler_name: string;
  product_ndc: string;
  dosage_form: string;
  product_type: string;
  marketing_category: string;
};

export type Drug = DrugMatch & {
  package_ndcs: string[];
  package_descriptions: string[];
  active_ingredients: string[];
  route: string[];
  application_number: string;
  listing_expiration_date: string;
  marketing_start_date: string;
  finished: boolean | null;
};

export type DrugSearchResponse = {
  query: string;
  matches: DrugMatch[];
};

export type DeviceMatch = {
  record_key: string;
  device_identifier: string;
  brand_name: string;
  company_name: string;
  version_or_model_number: string;
  catalog_number: string;
  product_code: string;
};

export type Device = Omit<DeviceMatch, "product_code"> & {
  device_description: string;
  product_codes: string[];
  commercial_distribution_status: string;
  prescription_otc_status: string;
  single_use_indicator: string;
  sterility_information: string;
  mri_safety_information: string;
  implantable_device_indicator: string;
  latex_information: string;
  storage_and_handling_conditions: string[];
  packaging_configurations: string[];
};

export type DeviceSearchResponse = {
  query: string;
  matches: DeviceMatch[];
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export type AnalysisResponse = {
  content: string;
  model_id: string | null;
  used_fallback: boolean;
  error: string | null;
};

export type AdverseEventAnalytics = {
  matching: {
    field: string;
    value: string;
    start_date: string;
    end_date: string;
  };
  retrieval: {
    retrieved_reports: number;
    available_reports: number;
    retrieval_limit: number;
    truncated: boolean;
    sort: string;
  };
  overview: {
    total_reports: number;
    serious_reports: number;
    non_serious_reports: number;
    serious_percentage: number;
    reporting_period_start: string | null;
    reporting_period_end: string | null;
  };
  outcomes: Array<{
    outcome: string;
    label: string;
    report_count: number;
  }>;
  trends: Array<{
    period: string;
    total_reports: number;
    serious_reports: number;
  }>;
  reactions: Array<{
    term: string;
    report_count: number;
    report_percentage: number;
    serious_report_count: number;
  }>;
  limitations: string[];
  source: string;
};

export type DeviceAdverseEventAnalytics = {
  matching: {
    field: string | null;
    value: string | null;
    strategy: string;
    start_date: string;
    end_date: string;
    attempted: Array<{
      field: string;
      value: string;
      strategy: string;
    }>;
  };
  retrieval: {
    retrieved_reports: number;
    available_reports: number;
    retrieval_limit: number;
    truncated: boolean;
    sort: string;
  };
  overview: {
    total_reports: number;
    reporting_period_start: string | null;
    reporting_period_end: string | null;
  };
  event_types: Array<{
    event_type: string;
    label: string;
    report_count: number;
    report_percentage: number;
  }>;
  trends: Array<{
    period: string;
    total_reports: number;
    death_reports: number;
    injury_reports: number;
    malfunction_reports: number;
    other_reports: number;
  }>;
  device_problems: Array<{
    term: string;
    report_count: number;
    report_percentage: number;
  }>;
  patient_problems: Array<{
    term: string;
    report_count: number;
    report_percentage: number;
  }>;
  limitations: string[];
  source: string;
};

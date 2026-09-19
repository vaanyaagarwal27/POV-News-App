const OFFICIAL_REGION_VALUES = new Set([
  "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
  "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
  "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
  "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim",
  "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand",
  "West Bengal", "Andaman and Nicobar Islands", "Chandigarh",
  "Dadra and Nagar Haveli and Daman and Diu", "Delhi",
  "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
]);

// label: shown to the user
// value: stored and passed to pickStories — must match shared/schema.md exactly
const STATE_OPTIONS = [
  { label: "Andaman & Nicobar Islands",                  value: "Andaman and Nicobar Islands" },
  { label: "Andhra Pradesh",                             value: "Andhra Pradesh" },
  { label: "Arunachal Pradesh",                          value: "Arunachal Pradesh" },
  { label: "Assam",                                      value: "Assam" },
  { label: "Bihar",                                      value: "Bihar" },
  { label: "Chandigarh",                                 value: "Chandigarh" },
  { label: "Chhattisgarh",                               value: "Chhattisgarh" },
  { label: "Dadra & Nagar Haveli and Daman & Diu",       value: "Dadra and Nagar Haveli and Daman and Diu" },
  { label: "Delhi NCR",                                  value: "Delhi" },
  { label: "Goa",                                        value: "Goa" },
  { label: "Gujarat",                                    value: "Gujarat" },
  { label: "Haryana",                                    value: "Haryana" },
  { label: "Himachal Pradesh",                           value: "Himachal Pradesh" },
  { label: "Jammu & Kashmir",                            value: "Jammu and Kashmir" },
  { label: "Jharkhand",                                  value: "Jharkhand" },
  { label: "Karnataka",                                  value: "Karnataka" },
  { label: "Kerala",                                     value: "Kerala" },
  { label: "Ladakh",                                     value: "Ladakh" },
  { label: "Lakshadweep",                                value: "Lakshadweep" },
  { label: "Madhya Pradesh",                             value: "Madhya Pradesh" },
  { label: "Maharashtra",                                value: "Maharashtra" },
  { label: "Manipur",                                    value: "Manipur" },
  { label: "Meghalaya",                                  value: "Meghalaya" },
  { label: "Mizoram",                                    value: "Mizoram" },
  { label: "Nagaland",                                   value: "Nagaland" },
  { label: "Odisha",                                     value: "Odisha" },
  { label: "Puducherry",                                 value: "Puducherry" },
  { label: "Punjab",                                     value: "Punjab" },
  { label: "Rajasthan",                                  value: "Rajasthan" },
  { label: "Sikkim",                                     value: "Sikkim" },
  { label: "Tamil Nadu",                                 value: "Tamil Nadu" },
  { label: "Telangana",                                  value: "Telangana" },
  { label: "Tripura",                                    value: "Tripura" },
  { label: "Uttar Pradesh",                              value: "Uttar Pradesh" },
  { label: "Uttarakhand",                                value: "Uttarakhand" },
  { label: "West Bengal",                                value: "West Bengal" },
];

STATE_OPTIONS.forEach(({ label, value }) => {
  if (!OFFICIAL_REGION_VALUES.has(value)) {
    console.warn(`[stateOptions] "${label}" has value "${value}" which is not in the official region list.`);
  }
});

export default STATE_OPTIONS;

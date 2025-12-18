export type DocumentEntry = {
  pptx_name: string;
  creation_date: string;
  last_mod_date: string;
  [key: string]: any;
};

export function getMinMaxCreationDates(data: DocumentEntry[]) {
  if (!data || data.length === 0) {
    return {
      minDate: null,
      maxDate: null,
      minTimestamp: null,
      maxTimestamp: null,
    };
  }

  let minDate = new Date(data[0].creation_date);
  let maxDate = new Date(data[0].creation_date);

  data.forEach(item => {
    const created = new Date(item.creation_date);
    if (created < minDate) minDate = created;
    if (created > maxDate) maxDate = created;
  });

  return {
    minDate,
    maxDate,
    minTimestamp: minDate.getTime(),
    maxTimestamp: maxDate.getTime(),
  };
}

import pptDataJson from '@/data/Updated_data.json'

interface PPTData {
  file_id: string;
  pptx_name: string;
  pptx_path: string;
  last_mod_date: string;
  creation_date: string;
}

const pptData = pptDataJson as PPTData[];

export const getMinDate = (): Date | null => {
    if (!pptData || pptData.length === 0) {
        return null;
    }

    let minDate: Date = new Date(pptData[0].creation_date);

    for (let i = 1; i < pptData.length; i++) {
        const currentDate = new Date(pptData[i].creation_date);

        if (currentDate < minDate) {
            minDate = currentDate;
        }
    }

    return minDate;
};

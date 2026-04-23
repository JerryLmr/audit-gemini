import * as XLSX from 'xlsx';

export async function parseExcel(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const data = e.target?.result;
      if (data) {
        const workbook = XLSX.read(data, { type: 'binary' });
        let result = '';
        workbook.SheetNames.forEach(sheetName => {
          const sheet = workbook.Sheets[sheetName];
          result += `Sheet: ${sheetName}\n`;
          result += XLSX.utils.sheet_to_csv(sheet);
          result += '\n\n';
        });
        resolve(result);
      }
    };
    reader.onerror = reject;
    reader.readAsBinaryString(file);
  });
}

export function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = error => reject(error);
  });
}

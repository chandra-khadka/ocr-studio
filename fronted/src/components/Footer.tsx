export default function Footer() {
    return (
        <footer className="bg-white border-t">
            <div className="max-w-7xl mx-auto px-4 py-6 text-sm text-gray-500 flex items-center justify-between">
                <div>© {new Date().getFullYear()} Visionary AI OCR Studio (Demo)</div>
                <div>
                    Built by Sr. AI Engineer,&nbsp;
                    <a
                        href="https://www.linkedin.com/in/chandra-bahadur-khadka-963a21121/"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline"
                    >
                        Chandra Bahadur Khadka
                    </a>
                </div>
            </div>
        </footer>
    )
}

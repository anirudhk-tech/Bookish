import { BrowserRouter, Routes, Route } from "react-router-dom"
import { Navbar } from "@/components/Navbar"
import { Library } from "@/pages/Library"
import { BookDetail } from "@/pages/BookDetail"
import { Compare } from "@/pages/Compare"
import { Explore } from "@/pages/Explore"

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-bg text-text">
        <Navbar />
        <main>
          <Routes>
            <Route path="/"            element={<Library />}    />
            <Route path="/book/:id"    element={<BookDetail />} />
            <Route path="/compare"     element={<Compare />}    />
            <Route path="/explore"     element={<Explore />}    />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

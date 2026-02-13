#include <windows.h>
#include <sapi.h>

#include <iostream>
#include <string>
#include <vector>

namespace {

std::wstring Utf8ToWide(const std::string& input) {
  if (input.empty()) return std::wstring();
  const int size_needed = MultiByteToWideChar(
      CP_UTF8, 0, input.c_str(), static_cast<int>(input.size()), nullptr, 0);
  if (size_needed <= 0) return std::wstring();
  std::wstring output(size_needed, L'\0');
  MultiByteToWideChar(
      CP_UTF8, 0, input.c_str(), static_cast<int>(input.size()), output.data(), size_needed);
  return output;
}

std::string JoinArgs(int argc, char** argv) {
  std::string text;
  for (int i = 1; i < argc; ++i) {
    if (!text.empty()) text += " ";
    text += argv[i];
  }
  return text;
}

}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) {
    std::cerr << "Usage: wvab_speaker <text>\n";
    return 1;
  }

  const std::string text_utf8 = JoinArgs(argc, argv);
  const std::wstring text_wide = Utf8ToWide(text_utf8);
  if (text_wide.empty()) {
    return 1;
  }

  HRESULT hr = CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED);
  const bool com_initialized = SUCCEEDED(hr);
  if (!com_initialized && hr != RPC_E_CHANGED_MODE) {
    return 1;
  }

  ISpVoice* voice = nullptr;
  hr = CoCreateInstance(CLSID_SpVoice, nullptr, CLSCTX_ALL, IID_ISpVoice, (void**)&voice);
  if (FAILED(hr) || voice == nullptr) {
    if (com_initialized) CoUninitialize();
    return 1;
  }

  // Slightly faster speech than default.
  voice->SetRate(2);
  voice->SetVolume(100);
  hr = voice->Speak(text_wide.c_str(), SPF_ASYNC | SPF_PURGEBEFORESPEAK, nullptr);
  if (SUCCEEDED(hr)) {
    voice->WaitUntilDone(3000);
  }

  voice->Release();
  if (com_initialized) CoUninitialize();
  return SUCCEEDED(hr) ? 0 : 1;
}

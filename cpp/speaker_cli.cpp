// # --------------------------------------------------------------------------------------------- # 
// # | Name: Md. Shahanur Islam Shagor                                                           | # 
// # | Autonomous Systems & UAV Researcher | Cybersecurity    | Specialist | Software Engineer   | #
// # | Voronezh State University of Forestry and Technologies                                    | # 
// # | Build for Blind people within 15$                                                         | # 
// # --------------------------------------------------------------------------------------------- # 
#include <windows.h>
#include <sapi.h>

#include <iostream>
#include <string>

namespace {

std::wstring JoinWideArgs(int argc, wchar_t** argv) {
  std::wstring text;
  for (int i = 1; i < argc; ++i) {
    if (!text.empty()) text += L" ";
    text += argv[i];
  }
  return text;
}

}  // namespace

int wmain(int argc, wchar_t** argv) {
  if (argc < 2) {
    std::cerr << "Usage: wvab_speaker <text>\n";
    return 1;
  }

  const std::wstring text_wide = JoinWideArgs(argc, argv);
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

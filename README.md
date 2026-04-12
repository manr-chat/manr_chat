# MANR

<img src="manr/resources/img/logo.png">

MANR (/ˈmɛnɐ/, from German word "Männer" for men) is an alternative chat client for the Grindr social network which aims to provide a better user experience. It is an unofficial client and in no way related to or endorsed by Grindr, Inc. The software is a reimplementation of the client side and contains no code from the official client.

## Installation

TODO

Download repository, install Python and third party dependencies.

## Features

As of now, MANR contains basic chat functionality which is most commonly used. Certain features are still missing, either because they are rarely used and thus not implemented yet, or because I consider them unnecesary.

Features include:
- Browse list of nearby user profiles, explore locations, and view "right now" profiles
- Set location
- View profile details of users
- Chat with users
- View received albums
- Upload pictures
- Send taps
- Add favorites, view list of favorites
- View list of users you received taps from or sent taps to.
- Manage multiple user accounts

Missing features:
- Creating an account. Please use the official app to create an account and then enter your account credentials (email, password) into the login dialog
- Changing own user profile text / stats / profile picture.
- Creating and sending albums. (Note: sending individual pictures is implemented)
- Translations, including server provided translations for tags, genders, etc.
- "Taken on Grindr" watermark
- Some other minor fields in the user profile
- "For You" profiles and "Explore locations" in the user grid. These are stupid anyway and won't be implemented.

## License

You may use this software under either the [CC0](https://creativecommons.org/public-domain/cc0/) license or the [Unlicense](LICENSE), per your choice.

### Third party code

This repository contains vendored copies of the following open source libraries:

- [Leaflet](https://leafletjs.com): an open-source JavaScript library for mobile-friendly interactive maps. [(BSD 2-Clause License)](manr/leaflet/LICENSE)
- [grindr-access](https://github.com/Slenderman00/grindr-access): A simple module for accessing the Grindr REST API.
MANR builds on this functionality, but contains a fork that is heavily modified and extended. [(MIT License)](manr/grindr_access/LICENSE)

### Disclaimer

Unauthorized use or misuse may violate Grindr Inc.'s terms of service and could result in account suspension. Use this at your own risk.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
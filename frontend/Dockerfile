FROM node:20.17.0

RUN mkdir -p /usr/src/app/next

WORKDIR /usr/src/app/next

COPY package*.json ./
COPY yarn.lock ./

RUN yarn install

COPY . .

RUN yarn build

RUN ls

EXPOSE 3000

CMD [ "yarn", "start" ]
